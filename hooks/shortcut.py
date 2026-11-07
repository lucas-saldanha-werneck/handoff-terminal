#!/usr/bin/env python3
"""UserPromptSubmit: send a message straight to a new terminal Claude Code session.

In a desktop app session, type either of these:
    terminal: <request>
    /terminal <request>
The hook stops the message before the app's model reads it and starts a terminal session
in the same folder with <request> as its first message. The request is the user's own text,
so it goes through as typed.
"""
import os
import re
import shlex
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as c  # noqa: E402

# "/terminal-setup" and other commands that only start with "/terminal" do not match.
PATTERN = re.compile(r"^\s*(?:/terminal(?=\s|$)|terminal\s*:)\s*(.*)$", re.S | re.I)


def block(reason):
    c.emit({"decision": "block", "reason": reason,
            "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "suppressOriginalPrompt": True}})


def main():
    if not c.is_app_session():
        return
    data = c.read_stdin_json(sys.stdin)
    if not data:
        return
    m = PATTERN.match(data.get("prompt") or "")
    if not m:
        return
    request = m.group(1).strip()
    if not request:
        block("terminal: add the request after the colon, e.g. terminal: sign in to example.com")
        return
    cwd = data.get("cwd") or ""
    if not os.path.isdir(cwd):
        cwd = os.path.expanduser("~")
    name = "terminal " + time.strftime("%H%M")
    cmd = [c.LAUNCHER, cwd, name, request]
    if c.dry_run():
        ok, out = True, "DRY " + " ".join(shlex.quote(x) for x in cmd)
    else:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
            ok, out = r.returncode == 0, c.one_line((r.stdout or "") + " " + (r.stderr or ""), 200)
        except (OSError, subprocess.TimeoutExpired) as e:
            ok, out = False, c.one_line(repr(e), 200)
    c.log("shortcut=%s name=%s" % ("ok" if ok else "failed", name))
    if ok:
        block("Sent to a terminal session named \"%s\" (folder %s). Follow it in your session list."
              % (name, cwd) + (" [%s]" % out if c.dry_run() else ""))
    else:
        block("Could not start the terminal session: %s" % out)


if __name__ == "__main__":
    main()
