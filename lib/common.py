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
import shlex
import sys
import time
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin")
WINDOWS = os.name == "nt"
if WINDOWS:
    # The Windows console code page can't print "→", "—" or "…"; the print would fail and the
    # hook would say nothing. UTF-8 output fixes it for every hook and command.
    for _stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            _stream.reconfigure(encoding="utf-8", errors="replace")


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
# "all" (default): sign in, fill in personal data, API keys and payment details, pay, buy and create
#   accounts. Paying, buying and creating accounts also need the user's own words asking for them.
# "sign-in": the terminal session only signs in.
SCOPE = "sign-in" if _setting("CLAUDE_PLUGIN_OPTION_SCOPE", "HANDOFF_SCOPE").lower() == "sign-in" else "all"
WAIT_MAX = int(os.environ.get("HANDOFF_WAIT_SECONDS") or 1800)
RETENTION_DAYS = 7
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,63}$")
MARKER = "HANDOFF-TERMINAL"


# ---------------------------------------------------------------- environment

def is_app_session():
    """True only inside a Claude desktop app session (or when a test forces it)."""
    if os.environ.get("HANDOFF_CHILD"):
        return False  # the terminal session we started: never hand off again
    if os.environ.get("HANDOFF_FORCE"):
        return True
    # The entrypoint can be INHERITED by a terminal session (a tmux server started from an app session
    # keeps CLAUDE_CODE_ENTRYPOINT=claude-desktop for every pane): a terminal above us means not the app.
    return os.environ.get("CLAUDE_CODE_ENTRYPOINT") == "claude-desktop" and not under_terminal()


def under_terminal():
    """True when an ancestor process has a terminal (the terminal's `claude`); app sessions have none.
    HANDOFF_UNDER_TERMINAL=1/0 forces the answer (tests). Unknown (no ps, Windows) = False."""
    forced = os.environ.get("HANDOFF_UNDER_TERMINAL")
    if forced in ("0", "1"):
        return forced == "1"
    import subprocess
    try:
        out = subprocess.run(["ps", "-axo", "pid=,ppid=,tty="], capture_output=True, text=True,
                             timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    procs = {}
    for ln in out.splitlines():
        parts = ln.split()
        if len(parts) >= 3 and parts[0].isdigit() and parts[1].isdigit():
            procs[int(parts[0])] = (int(parts[1]), parts[2])
    p, seen = os.getpid(), set()
    while p in procs and p not in seen and p > 1:
        seen.add(p)
        ppid, tty = procs[p]
        if tty not in ("??", "?", "-"):
            return True
        p = ppid
    return False


def dry_run():
    return bool(os.environ.get("HANDOFF_DRY"))


def read_stdin_json(stream):
    try:
        data = json.load(stream)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def emit(obj):
    # ASCII-only JSON (non-ASCII as \u escapes) reads the same in any code page.
    print(json.dumps(obj, ensure_ascii=True))


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


def write_private_once(path, text):
    """Like write_private, but never replaces a file that is already there.

    Returns False when the file already exists. The final step is atomic: os.link (and
    os.rename on Windows) fail if the target exists, so two writers cannot both win.
    """
    tmp = "%s.%d.%s.tmp" % (path, os.getpid(), secrets.token_hex(4))
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(tmp, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        try:
            os.link(tmp, path)
        except FileExistsError:
            return False
        except (OSError, NotImplementedError, AttributeError):
            # No hard links here (some file systems): rename refuses an existing target on
            # Windows; elsewhere check first (a tiny race, but no worse than before).
            if WINDOWS:
                try:
                    os.rename(tmp, path)
                except FileExistsError:
                    return False
                return True
            if os.path.lexists(path):
                return False
            os.replace(tmp, path)
        return True
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp)


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
    """Serialize hook runs for one app session (fcntl on macOS/Linux, msvcrt on Windows)."""
    fd = os.open(state_path(safe_name(name) + ".lock"), os.O_RDWR | os.O_CREAT, 0o600)
    if WINDOWS:
        import msvcrt
        while True:
            try:
                msvcrt.locking(fd, msvcrt.LK_LOCK, 1)  # tries for 10 s, then raises
                break
            except OSError:
                continue
        try:
            yield
        finally:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            os.close(fd)
        return
    import fcntl
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


# ---------------------------------------------------------------- commands

def quote_arg(text):
    """One shell argument. On Windows: double quotes and forward slashes, which Git Bash and
    PowerShell both accept."""
    if WINDOWS:
        return '"%s"' % str(text).replace("\\", "/").replace('"', '\\"')
    return shlex.quote(str(text))


def bin_cmd(name, *args):
    """Command line, for Claude to run, that calls one of the bin/ scripts.
    Windows can't run a script by its shebang, so the Python that runs this hook runs it."""
    parts = ([sys.executable] if WINDOWS else []) + [os.path.join(BIN, name)] + list(args)
    return " ".join(quote_arg(p) for p in parts)


def shell_hint():
    """Extra words for Claude on Windows, where its shell can be PowerShell."""
    return " (in PowerShell, put `& ` in front of it)" if WINDOWS else ""


def launcher_argv(*args):
    """argv that starts the launcher. A Python launcher on Windows runs through this Python."""
    if WINDOWS:
        try:
            with open(LAUNCHER, "rb") as f:
                head = f.read(64)
        except OSError:
            head = b""
        if head.startswith(b"#!") and b"python" in head or LAUNCHER.endswith(".py"):
            return [sys.executable, LAUNCHER] + list(args)
    return [LAUNCHER] + list(args)


def new_id():
    return time.strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(3)


def digest(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def result_path(hid):
    return os.path.join(STATE, "result-%s.json" % hid)


# ---------------------------------------------------------------- password managers

# (name, command). Only the command's presence on PATH is checked; nothing is run.
PASSWORD_CLIS = (
    ("1Password", "op"),
    ("Bitwarden", "bw"),
    ("Bitwarden (rbw)", "rbw"),
    ("Proton Pass", "pass-cli"),
    ("Dashlane", "dcli"),
    ("Keeper", "keeper"),
    ("LastPass", "lpass"),
    ("KeePassXC", "keepassxc-cli"),
    ("pass", "pass"),
    ("gopass", "gopass"),
)
SYSTEM_STORES = {"darwin": ("macOS Keychain", "security"), "linux": ("Secret Service (libsecret)", "secret-tool")}


def password_clis():
    """Password manager command-line tools found on PATH, as (name, command) pairs."""
    import shutil
    found = [(n, cmd) for n, cmd in PASSWORD_CLIS if shutil.which(cmd)]
    system = SYSTEM_STORES.get(sys.platform)
    if system and shutil.which(system[1]):
        found.append(system)
    return found


def done_effect(windows=None):
    """What handoff-done does after it records the result, as told to the terminal session."""
    if WINDOWS if windows is None else windows:
        return ("It records the result for the app. On Windows this window does not close by itself: "
                "after the command, stop and leave the window for the user to close.")
    return "It records the result for the app and closes this terminal session 20 seconds later."


# ---------------------------------------------------------------- version

def plugin_version(root=None):
    data = read_json(os.path.join(root or ROOT, ".claude-plugin", "plugin.json")) or {}
    return str(data.get("version") or "0")


def marketplace(root=None):
    """Marketplace this copy was installed from. Installed plugins live in
    ~/.claude/plugins/cache/<marketplace>/<plugin>/<version>; anything else (a clone, --plugin-dir)
    counts as the catalog, lucas-tools."""
    parts = os.path.normpath(root or ROOT).split(os.sep)
    if len(parts) >= 4 and parts[-4] == "cache":
        return parts[-3]
    return "lucas-tools"


def plugin_id(root=None):
    return "handoff-terminal@" + marketplace(root)


def version_tuple(text):
    """"0.10.2" -> (0, 10, 2). Anything that is not a number counts as 0."""
    parts = []
    for piece in str(text or "").strip().lstrip("v").split(".")[:4]:
        m = re.match(r"\d+", piece)
        parts.append(int(m.group()) if m else 0)
    return tuple(parts) or (0,)


def is_newer(latest, current):
    return version_tuple(latest) > version_tuple(current)
