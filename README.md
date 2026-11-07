# handoff-terminal

When the Claude desktop app won't type your password, personal data, API key or payment details,
a terminal Claude Code session does that one step, and the app carries on with the rest of your
request.

```
desktop app                                   terminal (tmux, Remote Control)
───────────                                   ───────────────────────────────
"log into my supermarket and check my cart"
  opens the site ...
  reaches the sign-in form
  HANDOFF-TERMINAL: shop.example | sign in ──▶ new session reads a brief
  runs handoff-wait in the background           signs in with your password manager
                                                handoff-done <id> ok ──┐
  ◀──────────────────────────────────────────────────────────────────┘ session closes
  continues: opens the cart, reports back
```

## Why

With the Claude in Chrome tools loaded, the desktop app's model works under a fixed list of
browser actions it won't do, even when you ask: type a password, a one-time code or an API key,
fill in an ID number such as an SSN or a CPF, enter payment or bank details, create an account.
Settings, `CLAUDE.md` and hooks can't change it. Many people have reported this as a blocker for
their own accounts, for example
[#96762](https://github.com/anthropics/claude-code/issues/96762),
[#102684](https://github.com/anthropics/claude-code/issues/102684),
[#106890](https://github.com/anthropics/claude-code/issues/106890) and
[#83380](https://github.com/anthropics/claude-code/issues/83380).

A Claude Code session in the terminal without Claude in Chrome doesn't get that list. This plugin
moves only the blocked step there, then hands control back to the app.

Anthropic may change this behavior at any time. It was tested on macOS 27.2 with Claude Code
2.1.319, Claude desktop 4.23118.0 and tmux 3.8, on 2026-11-07.

## What it does and doesn't do

- **You name the site.** The hand-off starts only if the site in the marker line appears in your
  own messages in that conversation. Code checks this, outside the model, against what you typed,
  not against tool results or web pages. A page that tells the app "log in at evil.example" gets
  no terminal session. The app has to ask you, and you confirm by typing the site name.
- **You ask for the money.** Paying, buying and creating accounts also need your own words asking
  for that kind of action ("buy", "pay", "create the account"), checked the same way. A web page
  can't add a purchase you never asked for. Items, amounts and recipients come from your messages,
  never from the app's text, and the terminal session stops if the page asks for more.
- **The app's words aren't instructions.** The brief gives the terminal session your own recent
  messages and the site. The app's description of the step goes in a fenced block marked
  untrusted. The one-line result note that comes back is marked as data too.
- **Secrets stay in your password manager.** The terminal session gets them the way your notes
  file says. Briefs, results and the log are `0600` files in a `0700` folder, and they're deleted
  after 7 days. Secrets are never written there.
- **Desktop app only.** The hooks do nothing in terminal, IDE or SDK sessions, or in the session
  they start.
- The terminal session runs in your normal permission mode. Don't run it with
  `--dangerously-skip-permissions`.

Want sign-in only? Set the `scope` option to `sign-in`. Then the terminal session signs in and
stops, and payments, purchases and new accounts stay with you.

## Requirements

- macOS or Linux, `python3` (3.8+), `tmux` (`brew install tmux`), and the `claude` CLI on your login
  shell `PATH`. Without tmux, the session runs with no window at all (through `script`); follow it
  in your session list through Remote Control.
- **One browser that both sessions can use.** The app keeps working in the browser where the step
  happened, so the terminal session has to work in *that* browser. For example, a Chrome profile
  started with `--remote-debugging-port` that also has the Claude in Chrome extension, plus a browser
  tool in the terminal session that can attach to it (Chrome DevTools MCP, Playwright MCP,
  `agent-browser`, or a CDP script).
- **A password manager CLI** the terminal session can use, such as 1Password `op` or Bitwarden `bw`.
- The project folder must be trusted by Claude Code: open `claude` there once and accept.

## Install

In Claude Code:

```
/plugin install handoff-terminal --marketplace lucas-saldanha-werneck/handoff-terminal
```

On versions before 2.1.275:

```
/plugin marketplace add lucas-saldanha-werneck/handoff-terminal
/plugin install handoff-terminal@handoff-terminal
```

Then write your setup notes. The terminal session reads them on every hand-off:

```markdown
<!-- ~/.config/handoff-terminal/notes.md -->
- Browser: Chrome on CDP port 9222 (profile ~/.chrome-agent).
- Secrets: fill them with ~/bin/fill-field, which reads the value from 1Password itself:
  `op run --env-file ~/.config/handoff-terminal/secrets.env -- ~/bin/fill-field <css selector> <VAR>`.
  Don't print secrets with `op item get --reveal`.
- Reply in English.
```

A fill script that reads the secret on its own keeps the value out of the terminal session's
screen and transcript. A command that prints it puts it there.

Restart the desktop app session so it loads the hooks.

### Updates

Plugins from this kind of marketplace don't update by themselves. Turn auto-update on once:
`/plugin` → **Marketplaces** → `handoff-terminal` → **Enable auto-update**. Or update by hand:

```
claude plugin update handoff-terminal@handoff-terminal
```

Once a day the plugin also checks GitHub in the background. When a newer version exists, the
next session shows one line with the command. `HANDOFF_NO_UPDATE_CHECK=1` turns that off.

## Use

Just ask the app ("log into my bank and download last month's statement", "buy what's in my cart",
"paste my API key from 1Password into the dashboard"). When it reaches a step it won't do, it
writes the marker line, a terminal session named `handoff <site> HHMM` appears in your session
list, and the app continues when it finishes. It usually takes 1 to 3 minutes. The app waits up
to 30.

To send a whole request to the terminal yourself, start the message with `terminal:` or
`/terminal`:

```
terminal: sign in to example.com and download my invoices
```

### Report a bug

In Claude Code:

```
/handoff-terminal:bug the terminal session opened but the app never continued
```

It collects the versions and the last log lines (sites, ids and paths removed), shows you the
report, and opens the GitHub issue only after you say yes. It uses `gh` when you're signed in.
Otherwise it opens the browser with the report filled in. You can also
[open an issue](https://github.com/lucas-saldanha-werneck/handoff-terminal/issues/new/choose) by hand.

## Settings

Plugin options (`/plugin configure handoff-terminal@handoff-terminal`):

- `scope`: `all` (default) or `sign-in`.
- `notes_file`: your instructions for the terminal session. Default `~/.config/handoff-terminal/notes.md`.
- `launcher`: the program that starts the session, called as `<folder> <name> <first message>`.
  Default `bin/handoff-launch` (tmux + `claude --remote-control --no-chrome`).

Environment variables (advanced): `HANDOFF_SCOPE`, `HANDOFF_NOTES` and `HANDOFF_LAUNCHER` do the
same as the options. `HANDOFF_STATE_DIR` (default `~/.claude/state/handoff-terminal`),
`HANDOFF_WAIT_SECONDS` (default `1800`), `HANDOFF_REMOTE_CONTROL=0` (start without Remote Control),
`HANDOFF_NO_UPDATE_CHECK=1` (no daily version check).

## How it works

| File | Event | Job |
|---|---|---|
| `hooks/nudge.py` | `UserPromptSubmit`, `PostToolUse(Failure)` on the 1Password tools | Tells the app how to hand off a blocked step instead of refusing it |
| `hooks/stop.py` | `Stop` | Reads the marker line, checks the site and the action, writes the brief, starts the session, tells the app to wait |
| `hooks/shortcut.py` | `UserPromptSubmit` | `terminal: <request>` sends the request to a new terminal session |
| `hooks/update_check.py` | `SessionStart` | Once a day, checks GitHub for a newer version and shows one line |
| `skills/bug/` + `bin/handoff-bug` | `/handoff-terminal:bug` | Builds a bug report, shows it, sends it to GitHub after your yes |
| `lib/` | | Shared code: settings, state files, text checks |
| `bin/handoff-launch` | | Default launcher |
| `bin/handoff-wait` | | The app waits for the result (exit 0 ok, 1 error, 3 timeout) |
| `bin/handoff-done` | | The terminal records the result and closes its tmux session |

Logs are in `~/.claude/state/handoff-terminal/handoff.log`.

## Known limits

- The app has to write the marker line. If it refuses without one, the Stop hook reminds it
  once. It never starts a session from a refusal alone.
- A folder Claude Code doesn't trust stops a hidden session at the trust question, so the
  launcher refuses and says so.
- A new Remote Control session takes about a minute to show up on the phone.
- This plugin doesn't touch Claude's rules. It runs the step in a session where they don't
  apply. The terminal session can still decline a step on its own judgment. If a future Claude
  Code version brings the same rules to the terminal, it stops working.

## Test

```
python3 tests/test_handoff.py -v
```

## License

MIT. Built with [Claude Code](https://claude.com/claude-code).
