---
description: Derive ordered, traceable tasks and validation work from an Agent Braid plan.
scripts:
  py: scripts/python/check_prerequisites.py --json
---

Consider the user's input: $ARGUMENTS

Run `{SCRIPT}` and read the feature's spec, plan and assurance record. Use the
overridden tasks template. Assign stable task IDs, requirement/scenario references,
target files, dependencies, verification commands and evidence obligations. Include
negative controls and scientific limitations. Mark parallelizable work as a
dependency property, not authorization to run agents concurrently. Distinguish
research completion from a hypothesis being supported. Do not implement tasks.
