"""Local admin commands: `HANDOFF-TERMINAL: local | sudo <command>`.

A few commands on the user's own computer need the administrator password (sudo), and the model does
not type it. Here the hook runs the command itself, in code: no terminal session, and the password
never reaches a model. sudo gets it from the user's own askpass program (`sudo -A`), which reads it
from their password manager.

Off until the user sets both settings:
- `sudo_commands`: the approved commands, comma separated ("renice, pmset, kill, shutdown -r").
  Each entry is a command name, optionally with the first arguments it must start with.
- `sudo_askpass`: a program that prints the administrator password (the SUDO_ASKPASS contract).

Rules, all checked in code:
- only a command that starts with an approved entry runs;
- the user's own messages must name the command (or say "sudo"), as with a site's domain;
- no shell: the step is split into arguments and run as is; shell syntax is refused;
- the program is looked up only in the system folders, so a look-alike in the user's PATH never runs
  as root.
"""
import os
import re
import shlex
import shutil
import subprocess

import common as c

SAFE_PATH = os.pathsep.join(("/usr/bin", "/bin", "/usr/sbin", "/sbin"))
SUDO = "/usr/bin/sudo"
RUN_TIMEOUT = 30  # the Stop hook has 45 s in all
# Characters that only mean something to a shell. Nothing here runs through one, so a step that has
# them was written for a shell and would not do what it says.
_SHELL = re.compile(r"[;&|<>`$(){}\\\n\r*?~!#\[\]]")
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}")


def _split_list(text):
    out = []
    for part in re.split(r"[,\n]", text or ""):
        try:
            tokens = shlex.split(part)
        except ValueError:
            continue
        if tokens and _NAME.fullmatch(tokens[0]) and tokens[0] != "sudo":
            out.append(tokens)
    return out


def approved():
    """The user's approved commands, each as a list of leading arguments. [] = none."""
    return _split_list(os.environ.get("CLAUDE_PLUGIN_OPTION_SUDO_COMMANDS")
                       or os.environ.get("HANDOFF_SUDO_COMMANDS") or "")


def askpass():
    """The user's askpass program, or "" when it is not set or cannot be run."""
    path = c._setting("CLAUDE_PLUGIN_OPTION_SUDO_ASKPASS", "HANDOFF_SUDO_ASKPASS")
    return path if path and os.path.isfile(path) and os.access(path, os.X_OK) else ""


def configured():
    return bool(approved() and askpass() and not c.WINDOWS)


def parse(step):
    """(argv, "") for a plain command, or (None, why). A leading `sudo` is dropped: the hook adds its own."""
    text = (step or "").strip().strip("`").strip()
    if not text:
        return None, "no command"
    if _SHELL.search(text):
        return None, "shell syntax (pipes, variables, redirects, wildcards) is not run"
    try:
        argv = shlex.split(text)
    except ValueError:
        return None, "the quotes do not match"
    if argv and argv[0] == "sudo":
        argv = argv[1:]
    if not argv:
        return None, "no command after sudo"
    if not _NAME.fullmatch(argv[0]):
        return None, "write the command by its plain name (no path, no options before it)"
    return argv, ""


def match(argv, entries):
    """The approved entry that argv starts with, or None."""
    for entry in entries:
        if argv[:len(entry)] == entry:
            return entry
    return None


def named_by_user(argv, user_texts):
    """True when the user's own messages write the command's name or the word "sudo"."""
    words = (re.escape(c.norm(argv[0])), "sudo")
    rx = re.compile(r"(?<![a-z0-9_.+-])(?:%s)(?![a-z0-9_+-])" % "|".join(words))
    return any(rx.search(c.norm(t)) for t in user_texts or [])


def program(name):
    """Full path of the command in the system folders, or ""."""
    return shutil.which(name, path=SAFE_PATH) or ""


def shown(argv):
    return "sudo " + " ".join(shlex.quote(a) for a in argv)


def run(argv, prog, helper):
    """Run `sudo -A -- prog args`. Returns (exit code or None, one line of output)."""
    env = dict(os.environ, SUDO_ASKPASS=helper)
    try:
        r = subprocess.run([SUDO, "-A", "--", prog] + argv[1:], capture_output=True, text=True, env=env,
                           timeout=RUN_TIMEOUT, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return None, "still running after %d s" % RUN_TIMEOUT
    except OSError as e:
        return None, "cannot run sudo: %s" % (e.strerror or e)
    return r.returncode, c.mask_secrets(c.one_line((r.stdout or "") + " " + (r.stderr or ""), 300))
