# Implementation plan

## Technical context and scope

Use the repository's Python >=3.12, stdlib-only implementation and unittest
conventions. Add a pure `agent_braid/trace_adapter.py` boundary later; reuse
`agent_braid.analysis.analyze` without modifying its rule set. Add only the
`analyze-trace` CLI path and explicitly versioned import/provenance contracts in
the implementation PR. Provider-specific work starts as offline research spikes
and never imports an SDK. The actual checkout branch for this planning delivery
is `work/foundation-backlog-20261005`; helper feature names are selectors.

## Constitution check before research

Articles 1/20 require analysis to remain useful without execution. Articles
5/13–16 require visible effect uncertainty, provenance and portable semantics.
Articles 19/21/25 require a concrete baseline and falsifiable usefulness;
Article 7 preserves mapping, analysis and decision boundaries. Clause zero and
Article 23 prohibit scientific upgrades from structural fixture results. ADR
0020's local MCP runtime domain is preserved. No MUST conflict or SHOULD
exception has been identified. No constitutional or existing contract change is
proposed here.

## Research, assumptions and alternatives

`research.md` records the inspected baseline and the decisions behind the generic
MVP. Select provider source versions using primary documentation before T006;
unavailable or contradictory versions are an inconclusive spike gate. Frozen
SPEC-011 records remain historical. Synthetic cases are the first corpus;
real-source permissions and privacy admission precede any real-data processing.
Prefer stdlib mapping over client dependencies, fixed mapper identifiers over
dynamic plugins, and explicit unknown over guessed fields.

## Design and compatibility

1. A versioned, metadata-only import request identifies source kind/schema,
   mapper, corpus admission, event/operation IDs, source hashes and records.
   A deterministic allowlist parser rejects duplicate members, bounds violations,
   unknown executable/content fields and invalid identities before analysis.
2. Separate source definition, operation instance and attempt identities. Require
   definition/input digests and explicit dependency/version coverage. Map known
   fields to AIM; retain bounded non-sensitive unsupported metadata and losses
   in provenance. Missing optional semantic coverage lowers effect coverage.
3. The generic path accepts one attempt per instance. Provider lifecycle spikes
   test whether pause/resume and multiple attempts are representable; preserve
   their timelines in provenance and report unsupported projection without
   emitting a stronger report. Do not create synthetic replacement identities
   that masquerade as source identities.
4. Call the existing analyzer on mapped AIM. Serialize its existing report
   unchanged and write provenance only to the caller's explicit safe local
   destination. Refuse collisions/symlinks and produce no partial success on
   rejected inputs. Report bytes and provenance bind each other by digests.
5. Add the proposed `analyze-trace` command with local paths and fixed mapper
   choice. The pure library returns artifacts without filesystem mutation;
   the CLI alone writes the explicit provenance file. No runtime/grant coupling.
6. Run generic controls, then separate OpenAI approval-lifecycle and MCP
   async-task/state spikes. Record source version, synthetic status, loss,
   uncertainty and decision. Screen A2A/NeMo/OTel without installing anything.

New interface/provenance versions, lifecycle unknown behavior and migration notes
are deliverables of T001. If a new public schema or architecture choice is needed,
its ADR/review precedes acceptance; existing AIM/report versions do not change.

## Validation strategy

The eight contracts in `quickstart.md` map REQ → SC → future tests → raw evidence.
Planned suite: `tests/test_trace_adapter.py`, with hostile input sentinels,
collisions, missing/stale fields, unknown coverage, multi-attempt rejection,
forbidden dispatch and deterministic baseline parity. Spy controls must observe
zero network/process/model calls rather than relying on absent CLI switches.
Provider spikes use fixed predeclared cases, a common generic/direct-AIM baseline
and retained-field/unsupported/false-safe counts with denominators. Missing fields
or cases remain visible and cannot be dropped to improve the result. Review the
mapping and privacy boundary separately from structural checks.

After implementation run the feature suite, `validate_spec_kit.py`, `quick` after
a coherent increment, and `pr` once on a stable candidate. Capture commit,
environment, commands, outcomes, raw artifacts and limits before changing draft
assurance. Clean-room or external reproduction is a separate evidence gate.

## Constitution check after design

No source lifecycle annotation is treated as a verified effect or execution
permission. No timestamp implies commutation or dependency. Unsupported coverage
cannot yield a stronger safety classification. The existing M4 runtime is neither
expanded nor re-certified by this importer. The design remains within Articles
1, 5, 7, 13–16 and 20; usefulness and independence hypotheses remain unproven.

## Human review and unresolved decisions

Generic synthetic implementation can begin with T001. Human review of new
interface/provenance contracts and security design remains pending. Provider
version choice, result interpretation and adoption are explicit T006–T008
outputs. Real-source admission, contact with providers and publication require
their own authority; this planning record supplies none of them.
