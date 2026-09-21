---
description: Implement authorized Agent Braid tasks with traceable tests and obtained evidence.
scripts:
  py: scripts/python/check_prerequisites.py --json --require-tasks --include-tasks
---

Consider the user's input: $ARGUMENTS

Run `{SCRIPT}`. Read spec, plan, tasks, assurance and analysis findings. Stop on
blocking contradictions, stale authorities or missing required review. Implement
only authorized tasks in dependency order. Execute the paired acceptance and
negative tests, record actual outputs and provenance in obtained evidence, and
mark tasks done only after their checks pass. Never manufacture a passing
scientific result. Run existing tests and all repository validators. Report
changes, executed checks, unexecuted checks, residual limits and review needs.
