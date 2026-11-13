# Security Policy

## Reporting a vulnerability

Please report it privately: open the repository's **Security** tab and choose **Report a vulnerability**
(https://github.com/lucas-saldanha-werneck/handoff-terminal/security/advisories/new). Please do not open a public issue for a
security problem.

## Supported versions

Only the latest release is supported. Fixes go into a new release.

## What handoff-terminal accesses

- Starts a terminal Claude Code session (`claude --remote-control`, in tmux or with no window; a minimized window on Windows) in the same folder, in your normal permission mode, so it also shows in your Remote Control session list. That session can use your password manager CLI and a browser as your notes file says, so it can sign in, and with the default `scope` also fill in personal or payment details, pay or create accounts. An automatic hand-off starts only for a site whose domain you typed in the conversation, and pays or creates accounts only when your own words asked for it.
- A message that starts with `terminal:` or `/terminal` goes to a new terminal session exactly as you typed it, with none of those checks and no secret masking, and is passed to it as a command-line argument.
- To write a brief it reads the app session's transcript (your last 3 messages, with text that looks like a password, API key, token or card number replaced), your notes file (`~/.config/handoff-terminal/notes.md` by default) and `~/.claude.json` (to check the folder is trusted). It checks which password manager CLIs are on your `PATH` but runs none of them.
- Writes briefs, results, markers and a log as `0600` files in a `0700` folder (`~/.claude/state/handoff-terminal/`). Briefs, results and markers are deleted after 7 days, the next time the hook runs in the app; the log (`handoff.log`: event lines with ids and site names, no message text) is not deleted.
- Network: once a day it fetches the plugin's own `plugin.json` from `raw.githubusercontent.com` to show an update notice. `handoff-bug`, only when you run it, reads the plugin options in `~/.claude/settings.json`, shows a bug report and files it as a public issue with `gh` or opens a prefilled GitHub issue page in your browser.
- Secrets come from the commands in your own notes file (for example `op run`), never from the app's text.
