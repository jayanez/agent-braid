---
description: Specify an Agent Braid feature or research protocol with traceable acceptance criteria and normative boundaries.
scripts:
  py: scripts/python/create_new_feature.py --json
---

Consider the user's input: $ARGUMENTS

Inspect existing specs first. For a new feature run `{SCRIPT}` with the requested
description, using the script's help for naming options; do not overwrite an
existing feature. Use `.specify/templates/overrides/spec-template.md` to populate
the feature's `spec.md`. Record user scenarios, stable requirements, exclusions,
ambiguities and measurable acceptance criteria without inventing implementation.
Create `assurance.json` as documented, with planned evidence and empty obtained
evidence at draft stage. Ask about material unknowns; do not silently assume
scientific claims. Report the feature identifier, actual checkout branch, artifacts
and unresolved questions; the helper's BRANCH_NAME is not evidence of a Git switch.
