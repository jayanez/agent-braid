---
name: "speckit-specify"
description: "Specify an Agent Braid feature or research protocol with traceable acceptance criteria and normative boundaries."
argument-hint: "Describe the feature you want to specify"
compatibility: "Requires spec-kit project structure with .specify/ directory"
metadata:
  author: "github-spec-kit"
  source: "templates/commands/specify.md"
user-invocable: true
disable-model-invocation: false
---


<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
<!-- Agent Braid policy adaptations by Juan Antonio Yáñez García, 2026.
Rendered with GitHub Spec Kit 1.0.7 (MIT); metadata identifies the adapter,
not authorship of these project policies. See docs/development/THIRD_PARTY.md. -->
## Agent Braid shared gates

Read `AGENTS.md`, `CONSTITUTION.md`, and `docs/development/SPEC_KIT.md` before
work. Paths in these instructions are relative to the repository root.
Run `python3 -m scripts.validate_spec_kit` before making changes. On failure,
report it and stop work in that checkout; do not regenerate to hide drift. Only
when the failure is `public repository contains unreachable objects` in a
shared local Git object store, restart the workflow in a fresh full clone of
the public `develop` branch with its own `.git`. Restore the reviewed SPEC-012
history using the command in `docs/development/SPEC_KIT.md`, then rerun the complete
preflight in that clone. Never prune the shared object store or suppress the
portable-root check as part of this recovery.

The root Constitution is the sole normative authority. The memory file is an
exact, generated replica, not an editable constitution template. Feature specs
are subordinate to the Constitution, applicable ADRs, operational semantics,
versioned schemas, and the limits of the actual evidence. A technical rationale
cannot authorize a contradiction with a constitutional MUST. Stop on conflicts;
record SHOULD deviations with rationale and review, and preserve MAY choices.
Only the dedicated amendment process can change constitutional obligations.

For each feature maintain `specs/<feature>/assurance.json` using the documented
record format. Cite applicable articles and repository documents. Give each
requirement, acceptance scenario and task a stable identifier. Trace requirement
to scenario, test and evidence. Separate planned evidence from obtained evidence;
record scope, assumptions, semantic domain, observation and execution contracts,
scientific limits, compatibility and evidence provenance. Capture current authority
hashes with `python3 -m scripts.validate_spec_kit snapshot specs/<feature>`. Before
human review, freeze a clean candidate with `python3 -m scripts.validate_spec_kit
freeze specs/<feature>`. Current snapshots detect working-tree drift; historical
snapshots remain bound to their reviewed commit and do not claim later authorities.
Snapshotting records bytes, never reviewer approval. Do not refresh stale current
hashes without reporting changed authorities and obtaining a new human review.
Evidence snapshots are independent: current evidence detects working-tree drift;
historical evidence and its embedded input hashes are verified at the frozen
candidate commit. Approval requires frozen authority and evidence snapshots.

Distinguish analogy, hypothesis, empirical finding and formal result. A hypothesis
is not a requirement to obtain a positive result. Negative and inconclusive
research outcomes are legitimate; assess protocol adherence separately from the
result. Passing deterministic checks does not prove constitutional semantics,
scientific validity, production safety, or a human approval.

Run `python3 -m scripts.validate_change --base develop --profile quick` after a
coherent implementation increment; sensitive or unknown paths escalate
conservatively. Run `--profile pr` once on a stable candidate before review or
integration. Feature-specific clean-room reproduction and evidence capture remain
separate boundary commands and must not be inferred from either profile. Analysis
and review are read-only.
Do not edit `CONSTITUTION.md` or its replica through any feature command.
Do not execute multiple agents, hooks, external issue creation, commits, pushes,
or autonomous delivery merely because a workflow suggests them. Those actions
require user authorization within the current task. Never infer approval from a
generated checklist or an evidence hash. Preserve unrelated user changes.


Consider the user's input: $ARGUMENTS

Inspect existing specs first. For a new feature run `python3 .specify/scripts/python/create_new_feature.py --json` with the requested
description, using the script's help for naming options; do not overwrite an
existing feature. Use `.specify/templates/overrides/spec-template.md` to populate
the feature's `spec.md`. Record user scenarios, stable requirements, exclusions,
ambiguities and measurable acceptance criteria without inventing implementation.
Create `assurance.json` as documented, with planned evidence and empty obtained
evidence at draft stage. Ask about material unknowns; do not silently assume
scientific claims. Report the feature identifier, actual checkout branch, artifacts
and unresolved questions; the helper's BRANCH_NAME is not evidence of a Git switch.
