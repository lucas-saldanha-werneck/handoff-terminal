---
name: bug
description: Report a handoff-terminal bug on GitHub. Collects the versions and a log with sites, ids and paths removed, shows you the report, and sends it only after you say yes.
argument-hint: "[what went wrong]"
disable-model-invocation: true
---

The user wants to report a bug in the handoff-terminal plugin. What they typed: $ARGUMENTS

1. If they did not say what went wrong, ask in one short question. Wait for the answer.
2. Write the problem in 1–3 plain sentences: what they did, what they expected, what happened.
   Leave out passwords, codes, card numbers, emails, names, addresses and site names.
3. Run:
   `python3 "${CLAUDE_PLUGIN_ROOT}/bin/handoff-bug" draft "<the sentences>"`
4. Show the user the whole report exactly as printed, and a short title (under 80 characters).
   Ask: "Send this to GitHub?" Say that the issue is public.
   If they want changes, edit the report file printed after `REPORT FILE:` and show it again.
5. Only after a clear yes, run:
   `python3 "${CLAUDE_PLUGIN_ROOT}/bin/handoff-bug" send "<report file>" --title "<title>"`
6. Give the user the link it prints. If it opened the browser, tell them to press Submit there.

Never send without the yes. Never add anything to the report that the user did not see.
