# Security Policy

## Reporting a vulnerability

Please report it privately: open the repository's **Security** tab and choose **Report a vulnerability**
(https://github.com/lucas-saldanha-werneck/handoff-terminal/security/advisories/new). Please do not open a public issue for a
security problem.

## Supported versions

Only the latest release (0.7.9) is supported. Fixes go into a new release.

## What handoff-terminal accesses

- Starts a terminal Claude Code session (in tmux, or windowless) for one step of a desktop app request. That session can use your password manager CLI and a real browser, so it can sign in, and with the default `scope` also pay or create accounts, but only for a site you confirm by typing its domain and, for payments, only when your own words asked for it.
- Writes briefs, results and a log as `0600` files in a `0700` state folder and deletes them after 7 days. Passwords, API keys, tokens and card numbers that look like secrets are removed from the messages copied into a brief.
- Network: once a day it fetches the plugin's own `plugin.json` from `raw.githubusercontent.com` to show an update notice. `handoff-bug`, only when you run it, shows a bug report and files it with `gh` or opens a prefilled GitHub issue page in your browser.
- Secrets come from the commands in your own notes file (for example `op run`), never from the app's text.
