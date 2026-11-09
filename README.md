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
- **Windows:** Python from
  [python.org](https://www.python.org/downloads/windows/) (the Python install manager adds the
  `python3` command the hooks call) and the `claude` CLI on `PATH`. The terminal session opens in a
  new minimized window. Close it yourself when the step is done. Tested with the desktop app
  (4.23118.0) on Windows 11 ARM64: marker, hidden terminal window, `handoff-done`, and the app
  carried on. Please report what you find with `/handoff-terminal:bug`.
- **One browser that both sessions can use.** The app keeps working in the browser where the step
  happened, so the terminal session has to work in *that* browser. For example, a Chrome profile
  started with `--remote-debugging-port` that also has the Claude in Chrome extension, plus a browser
  tool in the terminal session that can attach to it (Chrome DevTools MCP, Playwright MCP,
  `agent-browser`, or a CDP script).
- **A password manager CLI** the terminal session can use. 1Password, Bitwarden, Proton Pass,
  Dashlane, Keeper, LastPass, KeePassXC, pass, gopass and the system keychain all work. See
  [Password managers](#password-managers).
- The project folder must be trusted by Claude Code: open `claude` there once and accept.

## Install

In Claude Code:

```
/plugin marketplace add lucas-saldanha-werneck/claude-plugins
/plugin install handoff-terminal@lucas-plugins
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

### Password managers

The plugin looks for these tools on `PATH` and tells the terminal session which ones it found. It
only checks that the command exists. It never runs it. Your notes say which one to use and how.

| Manager | Read one field | Run a command with secrets, without printing them | Unlock | Tested |
| --- | --- | --- | --- | --- |
| 1Password `op` | `op read op://Vault/Item/password` | `op run --env-file=.env -- cmd` | `op signin` | ✅ |
| Proton Pass `pass-cli` | `pass-cli item view "pass://Vault/Item/password"` | `pass-cli run --env-file .env -- cmd` | `pass-cli login` (opens a browser sign-in) | paid plan only ⚠️ |
| Dashlane `dcli` | `dcli read dl://Item/password` | `dcli exec -- cmd` | `dcli sync` (asks email, a device code and the master password once) | ✅ |
| gopass | `gopass show Item --password` | `gopass env Item cmd` (sets `ITEM=<password>`) | GPG agent | ✅ |
| Bitwarden `bw` | `bw get password Item` | — | `bw unlock` (sets `BW_SESSION`) | ✅ |
| Bitwarden `rbw` | `rbw get Item` (`--field=F` for others) | — | `rbw unlock` | ✅ |
| LastPass `lpass` | `lpass show --password Item` (`--field=F`) | — | `lpass login <email>` | ✅ |
| KeePassXC | `keepassxc-cli show -a Password db.kdbx Item` | — | asks for the database password each time (reads it from stdin) | ✅ |
| pass | `pass show Item` (first line) | — | GPG agent | ✅ |
| Keeper `keeper` | `keeper find-password <UID or title>` | — | `keeper login` (then `this-device` for a persistent login) | ✅ |
| macOS Keychain | `security find-generic-password -s Service -a Account -w` | — | your Mac login | ✅ |
| Linux libsecret | `secret-tool lookup service Service` | — | your desktop login | ✅ |

The `.env` files above hold references, not values. For example, `DB_PASS=op://Vault/Item/password`
or `DB_PASS=dl://Item/password`. Check the exact reference format in your manager's docs.

For managers with no "run" command, the fill script reads the value into a variable itself, so the
terminal session never sees it:

```sh
# ~/bin/fill-password, called as: fill-password '<css selector>'
export PW="$(bw get password Github)"   # or rbw get / lpass show --password / pass show ... | head -1
~/bin/fill-field "$1" PW                # pass the variable's name, not the value
```

The terminal session can only use a manager that is already unlocked, or one it can unlock with no
prompt. A manager that waits for a master password on the screen stops the hand-off. Unlock it
before you start, or tell your notes how to unlock it (a biometric prompt, a session token file).

✅ = run for real on 2026-11-07 against a test item: Bitwarden and rbw against a local Vaultwarden
server, LastPass, Keeper and Dashlane with trial accounts.

What the tests showed:

- `op run` replaces the value with `<concealed by 1Password>` if the command prints it.
- `bw` and `rbw` refuse when two items share a name. Use a unique name or the item id.
- The npm build of `bw` needs Node 20 or later (on Node 18 it stops with "Web Crypto API is
  unavailable"). Bitwarden's standalone `bw` download has no such need.
- A self-hosted Bitwarden server must use HTTPS for `bw`.
- Proton Pass: a free account signs in and is then refused with "Your account is not yet allowed
  to use our CLI". The CLI needs a paid plan (Pass Plus or above).
- Dashlane: `dcli` only reads. Add items in the Dashlane app or browser extension. `dcli exec`
  runs its command through a shell as one string, so point it at a script instead of `sh -c '...'`.
- LastPass: set `LPASS_DISABLE_PINENTRY=1` to give the master password on stdin. A long
  `LPASS_HOME` path fails with "Path too large for agent control socket".

### Updates

Plugins from this kind of marketplace don't update by themselves. Turn auto-update on once:
`/plugin` → **Marketplaces** → `lucas-plugins` → **Enable auto-update**. Or update by hand:

```
claude plugin update handoff-terminal@lucas-plugins
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

Plugin options (`/plugin configure handoff-terminal@lucas-plugins`):

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
| `bin/handoff-done` | | The terminal records the result (the first one wins; a second call is refused) and closes its tmux session |

Logs are in `~/.claude/state/handoff-terminal/handoff.log`.

## Limits

- The app has to write the marker line. If it refuses without one, the Stop hook reminds it
  once. It never starts a session from a refusal alone.
- A folder Claude Code doesn't trust stops a hidden session at the trust question, so the
  launcher refuses and says so.
- A new Remote Control session takes about a minute to show up on the phone.
- This plugin doesn't touch Claude's rules. It runs the step in a session where they don't
  apply. The terminal session can still decline a step on its own judgment. If a future Claude
  Code version brings the same rules to the terminal, it stops working.

## Tests

```
python3 tests/test_handoff.py -v
```

## License

MIT. Built with [Claude Code](https://claude.com/claude-code).
