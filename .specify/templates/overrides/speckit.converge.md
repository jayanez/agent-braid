---
description: Assess Agent Braid implementation convergence against specifications and actual evidence without expanding scope.
scripts:
  py: scripts/python/check_prerequisites.py --json --require-tasks --include-tasks
---

Consider the user's input: $ARGUMENTS

Run `{SCRIPT}`. Compare implementation and obtained evidence with each requirement,
scenario and task. Run the deterministic gates. Report satisfied, failed, pending,
negative and inconclusive outcomes distinctly. If requested, append bounded
remaining tasks without rewriting completed history; otherwise report read-only.
Do not auto-loop into implementation, execute agents or delivery, approve reviews,
or weaken requirements to declare convergence. Completion requires actual evidence
for mandatory acceptance criteria; a legitimate negative research finding may
complete its protocol without supporting its hypothesis.
