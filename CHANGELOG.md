# Changelog

All notable changes to this project are documented here. Versions follow [Semantic Versioning](https://semver.org/).

## [0.7.10] - 2026-11-13
- Bug skill: the description says when to use it; version and tags; Purpose, Prerequisites, Limitations and Troubleshooting sections.
- README: demo video, plugin check and skill score badges; adds SECURITY.md.

## [0.7.9] - 2026-11-13
- Skill author, Instructions and Examples sections.

## [0.7.8] - 2026-11-12
- Secret-looking text in the user messages copied into the brief is masked; the brief allows only actions that passed the gate.
- The same site and step is not started again without a new user message; the windowless launcher checks the session is still running.
- Cleanup deletes only the plugin's own files; `/bug` passes free text through stdin.

## [0.7.7] - 2026-11-11
- Tighter site gate: the user must write a domain with the same registrable domain as the site.
- Negated mentions ("don't pay") do not count as asking for the action; `/compact` summaries are not read as the user's words.

## [0.7.6] - 2026-11-11
- A session with a terminal above it is not treated as an app session.

## [0.7.5] - 2026-11-11
- Points to the catalog repo's new name, `lucas-tools`.

## [0.7.4] - 2026-11-11
- Catalog renamed to `lucas-tools`.

## [0.7.3] - 2026-11-09
- Docs: short description, catalog install, common heading names.
- The update notice and the bug report use the catalog this copy came from.

## [0.7.2] - 2026-11-08
- `handoff-done`: the first result wins.
- README: marks which password manager CLIs were tested for real, and Windows 11 with the desktop app.

## [0.7.1] - 2026-11-07
- Windows: the brief no longer says the window closes in 20 seconds.

## [0.7.0] - 2026-11-07
- Works with any password manager CLI, not only 1Password.

## [0.6.0] - 2026-11-07
- Windows support.

## [0.5.1] - 2026-11-07
- Bug report reads the saved plugin options for scope and launcher.

## [0.5.0] - 2026-11-07
- Bug report command and a daily update check.

## [0.4.1] - 2026-11-07
- Windowless mode reads the full `ps` line and drops inherited `TMUX` variables.

## [0.4.0] - 2026-11-07
- No-tmux mode runs the session without a window; `handoff-done` closes it.

## [0.3.1] - 2026-11-07
- Launcher: trust above a git repository root does not count.

## [0.3.0] - 2026-11-07
- Broader purpose: personal data and API keys as well as sign-in and payments; `scope` defaults to `all`.

## [0.2.0] - 2026-11-07
- `scope` option: `sign-in` or `all`.

## [0.1.0] - 2026-11-07
- First release: sign-in hand-off from the Claude desktop app to a terminal session.
