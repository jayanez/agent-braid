---
description: Perform a read-only cross-artifact consistency and scientific-boundary review of an Agent Braid feature.
scripts:
  py: scripts/python/check_prerequisites.py --json --require-tasks --include-tasks
---

Consider the user's input: $ARGUMENTS

Run `{SCRIPT}`. Read spec, plan, tasks and assurance record. Check ambiguity,
coverage, contradictions, acceptance-test traceability, authority freshness and
planned versus obtained evidence. Report a finding ID, severity, exact location,
authority and proposed remediation for each issue. Constitutional MUST conflicts
block implementation; missing human review stays pending. Do not change files or
reinterpret a scientific hypothesis as a mandatory positive result.
