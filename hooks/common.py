"""Shared code for the handoff-terminal hooks and commands.

Everything here is standard-library Python 3.8+. Nothing in this file prints secrets or
writes them to disk: the state folder holds hand-off ids, site names, the user's own
recent prompts (in the brief, mode 0600) and one-line result notes.
"""
import contextlib
import hashlib
import json
import os
import re
import secrets
import time
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin")


def _setting(*names):
    """First non-empty value among plugin options (CLAUDE_PLUGIN_OPTION_*) and env vars."""
    for name in names:
        value = (os.environ.get(name) or "").strip()
        if value:
            return os.path.expanduser(value)
    return ""


STATE = _setting("HANDOFF_STATE_DIR") or os.path.expanduser("~/.claude/state/handoff-terminal")
NOTES = (_setting("CLAUDE_PLUGIN_OPTION_NOTES_FILE", "HANDOFF_NOTES")
         or os.path.expanduser("~/.config/handoff-terminal/notes.md"))
LAUNCHER = _setting("CLAUDE_PLUGIN_OPTION_LAUNCHER", "HANDOFF_LAUNCHER") or os.path.join(BIN, "handoff-launch")
# "sign-in" (default): the terminal session only signs in.
# "all": it may also pay, buy and create accounts, when the user asked for that in their own words.
SCOPE = "all" if _setting("CLAUDE_PLUGIN_OPTION_SCOPE", "HANDOFF_SCOPE").lower() in ("all", "tudo") else "sign-in"
WAIT_MAX = int(os.environ.get("HANDOFF_WAIT_SECONDS") or 1800)
RETENTION_DAYS = 7
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,63}$")
MARKER = "HANDOFF-TERMINAL"


# ---------------------------------------------------------------- environment

def is_app_session():
    """True only inside a Claude desktop app session (or when a test forces it)."""
    if os.environ.get("HANDOFF_CHILD"):
        return False  # the terminal session we started: never hand off again
    return (os.environ.get("CLAUDE_CODE_ENTRYPOINT") == "claude-desktop"
            or bool(os.environ.get("HANDOFF_FORCE")))


def dry_run():
    return bool(os.environ.get("HANDOFF_DRY"))


def read_stdin_json(stream):
    try:
        data = json.load(stream)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def emit(obj):
    print(json.dumps(obj, ensure_ascii=False))


def context(event, text):
    emit({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}})


# ---------------------------------------------------------------- text

_QUOTES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "“": '"', "”": '"',
                         " ": " ", "‑": "-", "–": "-", "—": "-"})


def norm(text):
    """Lower case, no accents, straight quotes, single spaces."""
    text = unicodedata.normalize("NFKD", (text or "").translate(_QUOTES))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r"[ \t]+", " ", text)


def compact(text):
    """Only letters and digits: "Zona Sul" -> "zonasul"."""
    return re.sub(r"[^a-z0-9]", "", norm(text))


def one_line(text, limit):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def fence(text):
    """Quote untrusted text so it cannot close the fence and pose as instructions."""
    body = str(text or "").replace("~~~", "~ ~ ~")
    return "~~~text\n" + body.strip() + "\n~~~"


# ---------------------------------------------------------------- files

def safe_name(value):
    return re.sub(r"[^A-Za-z0-9_-]", "", str(value or ""))[:64] or "unknown"


def valid_id(value):
    return bool(ID_RE.match(value or ""))


def ensure_state():
    os.makedirs(STATE, mode=0o700, exist_ok=True)
    try:
        os.chmod(STATE, 0o700)
    except OSError:
        pass
    return STATE


def state_path(name):
    return os.path.join(ensure_state(), name)


def write_private(path, text):
    """Write a new 0600 file atomically. Never follows a symlink at the target."""
    tmp = "%s.%d.%s.tmp" % (path, os.getpid(), secrets.token_hex(4))
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(tmp, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def log(message):
    """One line per event. Only ids, sites and status, never prompt text."""
    try:
        path = state_path("handoff.log")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + one_line(message, 400) + "\n")
    except OSError:
        pass


def prune():
    """Delete briefs, results and markers older than RETENTION_DAYS."""
    limit = time.time() - RETENTION_DAYS * 86400
    try:
        names = os.listdir(STATE)
    except OSError:
        return
    for name in names:
        if name == "handoff.log" or name.endswith(".lock"):
            continue
        path = os.path.join(STATE, name)
        with contextlib.suppress(OSError):
            if os.path.getmtime(path) < limit:
                os.unlink(path)


@contextlib.contextmanager
def locked(name):
    """Serialize hook runs for one app session (fcntl, POSIX only)."""
    import fcntl
    fd = os.open(state_path(safe_name(name) + ".lock"), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def new_id():
    return time.strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(3)


def digest(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def result_path(hid):
    return os.path.join(STATE, "result-%s.json" % hid)
