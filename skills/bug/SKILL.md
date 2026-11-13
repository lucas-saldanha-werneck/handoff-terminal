---
name: bug
description: 'Report a handoff-terminal bug on GitHub. Use when the user wants to report a problem with the handoff-terminal plugin. Collects the versions and a log with sites, ids and paths removed, shows the user the report, and sends it only after a clear yes.'
argument-hint: "[what went wrong]"
disable-model-invocation: true
version: "0.7.10"
metadata:
  author: Lucas Saldanha Werneck <lucas@2olhares.com>
  tags: [bug-report, github, support]
---

# Report a handoff-terminal bug

## Purpose

Let the user report a handoff-terminal bug in one step: a draft report with versions and a cleaned log, shown in full before anything is sent.

The user wants to report a bug in the handoff-terminal plugin. What they typed: $ARGUMENTS

## Instructions

1. If they did not say what went wrong, ask in one short question. Wait for the answer.
2. Write the problem in 1–3 plain sentences: what they did, what they expected, what happened.
   Leave out passwords, codes, card numbers, emails, names, addresses and site names.
3. Run this, with the sentences between the two `EOF` lines. The quoted `'EOF'` keeps the shell
   from running anything inside the text (`$(...)`, backticks):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/handoff-bug" draft - <<'EOF'
   <the sentences>
   EOF
   ```
4. Show the user the whole report exactly as printed, and a short title (under 80 characters).
   Ask: "Send this to GitHub?" Say that the issue is public.
   If they want changes, edit the report file printed after `REPORT FILE:` and show it again.
5. Only after a clear yes, run (the title goes between the `EOF` lines the same way):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/bin/handoff-bug" send "<report file>" --title - <<'EOF'
   <title>
   EOF
   ```
6. Give the user the link it prints. If it opened the browser, tell them to press Submit there.

Never send without the yes. Never add anything to the report that the user did not see.

## Prerequisites

- python3 (3.8+) and the handoff-terminal plugin enabled.
- Optional: a signed-in gh CLI. Without it, sending opens the browser on a new issue with the report already filled in.

## Limitations

- The issue is public: the user must see and approve the whole report first.
- Names, passwords, codes, addresses and site names are left out of the sentences; the log has sites, ids and paths removed.

## Troubleshooting

- Error "no report at ...": the draft step was skipped. Run it first.
- Error from gh (it could not create the issue): the tool says so and uses the browser instead; tell the user to press Submit there.

## Examples

- `/handoff-terminal:bug the terminal session opened but the app never continued`: writes the problem in a
  few plain sentences, runs `handoff-bug draft`, shows the whole report and a short title, and asks
  "Send this to GitHub?". Only after a clear yes does it run `handoff-bug send` and give the link.
- `/handoff-terminal:bug` with nothing after it: asks in one short question what went wrong, then continues the same way.
- The user wants a change to the draft: edit the report file printed after `REPORT FILE:` and show it again before asking.
