#!/usr/bin/env python3
"""SessionStart hook: tell the user when a newer handoff-terminal is on GitHub.

Plugins from third-party marketplaces do not update by themselves (auto-update is off by
default). So, at most once a day, this hook looks up the version on GitHub in a background
process (the session never waits for the network), and the next session start shows one line
when a newer version exists. HANDOFF_NO_UPDATE_CHECK=1 turns it off.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import common as c  # noqa: E402

URL = os.environ.get("HANDOFF_UPDATE_URL") or \
    "https://raw.githubusercontent.com/lucas-saldanha-werneck/handoff-terminal/main/.claude-plugin/plugin.json"
DAY = 86400
CACHE = "update-check.json"


def cache():
    return c.read_json(os.path.join(c.STATE, CACHE)) or {}


def save(data):
    c.write_private(c.state_path(CACHE), json.dumps(data))


def fetch():
    """Background part: read the version on GitHub and store it. Quiet on any error."""
    data = cache()
    data["checked"] = time.time()  # also on failure, so an offline Mac does not retry every session
    try:
        with urllib.request.urlopen(URL, timeout=8) as r:
            latest = json.loads(r.read(65536).decode("utf-8")).get("version")
        if latest:
            data["latest"] = str(latest)
    except Exception:
        pass
    save(data)


def message(latest, current):
    return ("handoff-terminal %s is out (you have %s). Update: claude plugin update "
            "handoff-terminal@handoff-terminal — or turn on auto-update in /plugin → "
            "Marketplaces → handoff-terminal." % (latest, current))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--fetch":
        fetch()
        return
    event = c.read_stdin_json(sys.stdin) or {}
    if (os.environ.get("HANDOFF_NO_UPDATE_CHECK") or os.environ.get("HANDOFF_CHILD")
            or event.get("source") not in (None, "startup", "resume")):
        return
    data, now = cache(), time.time()
    current = c.plugin_version()
    latest = data.get("latest")
    if latest and c.is_newer(latest, current) and now - float(data.get("shown") or 0) > DAY:
        data["shown"] = now
        save(data)
        c.emit({"systemMessage": message(latest, current)})
    if now - float(data.get("checked") or 0) > DAY:
        if os.environ.get("HANDOFF_UPDATE_SYNC"):  # tests
            fetch()
        else:
            subprocess.Popen([sys.executable, os.path.abspath(__file__), "--fetch"],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # an update check must never break a session
