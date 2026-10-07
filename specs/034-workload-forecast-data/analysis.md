# FC.1 planning consistency assessment

Date: 2026-10-07. Scope: the draft SPEC-034–037 packet and its source tracking.
This is an author self-assessment, not an independent model review, source-rights
decision, installed-model test, scientific validation or founder approval.

## Findings resolved during drafting

1. The repository feature selector can prefer `.specify/feature.json` over the
   short environment feature name. Each quickstart now sets both
   `SPECIFY_FEATURE` and `SPECIFY_FEATURE_DIRECTORY`; the setup and prerequisite
   helpers were checked separately against each of the four actual directories.
2. Source feasibility must not inspect calibration/holdout outcome values.
   SPEC-034/REQ-006, its assurance, source register and task obligations restrict
   action/outcome variability inspection to the development pilot. Counts and
   masks can establish completeness without exposing held-out outcome values.
3. Generic Chronos documentation labels a point output as mean. Inspection of
   the proposed released Chronos-2 implementation assigns that output from the
   0.5 quantile. SPEC-035 labels it median/p50, with installed conformance still
   required before accepting the adapter.
4. The current runtime has a bounded local execution language. Advice selects
   only its admitted serial/parallel policies and reviewed local capacity;
   resource forecasts do not admit new hosts, waves, grants or execution domains.
5. A forecast benchmark does not establish economic utility. SPEC-036 separately
   measures actual matched policy outcomes, full cost and episode-level
   uncertainty, retaining failures and legitimate negative/inconclusive exits.

## Structural coverage

The four specs contain 27 requirement/scenario pairs and 33 unchecked tasks.
Every requirement has a task reference and prospective validation procedure;
the cross-spec task graph is acyclic. Local Markdown targets and the source
tracking inventory resolve. All four authority snapshots match the current
authorities. All obtained acceptance evidence lists are empty and human review
remains pending. No existing spec task state, tracking override or milestone
state was changed by this packet.

Validation profiles provide executed repository-check results separately from
these planned feature procedures. An existing full-suite pass does not implement
or validate the future forecast modules.

## Decisions still required

- Source owners, capture rights/privacy and complete prospective source yield.
- Exact target utility, actual resource diversity and development-only pilot
  feasibility for the proposed cadence, episode count and threshold.
- Full dependency/artifact/license review, file hashes, CPU enforcement and
  installed Chronos conformance/cold and resident costs.
- Immutable launch registration, exact numerical budgets and independent
  operator authority for every actual arm.
- Bounded human interpretation and any later exact-capability promotion.

The candidate JSON manifests intentionally contain null approval/budget fields
and false authorization flags. They are review drafts, not executable launch
receipts. There is no unresolved structural blocker in the authored plan;
the listed evidence and authority gates remain open.
