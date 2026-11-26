# SPEC-043: Evidence-oriented AI tooling developer journey

**Milestone:** M4.5 — AI tooling integrations for Codex and Claude Code

**Status:** draft specification (`assurance.json`: stage `draft`, human review
`pending`). Experimental implementation and bounded local evidence exist: T002 and
T004–T007 are done with `evidence/sc-002.json` and `sc-004.json` to `sc-007.json`,
and so are the technical counterparts T011–T014. T001, T003 and T008 are Deferred by
the [2026-10-31 owner decision](../044-ai-tooling-evaluation/owner-decision-20261031-m45-closure.md),
and T009 and T010 depend on them. Native-host acceptance, independent review and
founder acceptance are pending.

## Purpose and scope

Expose a complete guided developer journey with faithful chat explanations, interaction graph and offline evidence exports.

## Authorities

Constitution clause zero and Articles 3–7, 12–16, 19–25; GOVERNANCE.md; operational semantics, claim discipline, ADRs 0019/0020 and proposed ADR 0021. This spec is subordinate to accepted authorities. See assurance.json for references and authority inventory.

Actors: the developer, who follows the journey and requests execution (REQ-001,
SC-003); the operator, who supplies the existing exact grant outside MCP
(`contracts/presentation.md`, mandatory journey; SC-003 "operator scope"); the two
supported hosts, Codex and Claude Code (REQ-001, REQ-008); and the founder, who records
the human decision (T010). No other role interacts with this feature.

Exclusions (scope statements; no REQ covers them literally, per the owner decision
recorded in `evidence/owner-decisions-20261126.md`):

- Existing AIM/runtime/grant/verifier contracts remain unchanged (`assurance.json`
  `scientific_limits`).
- No source ref promotion, repository-code/hook execution, arbitrary network effects
  or new scientific guarantee (`assurance.json` `scientific_limits`). REQ-004 covers
  only that a result display does not imply source promotion (SC-004); REQ-007
  covers only that exports use no network or telemetry (SC-007).
- Host permission never substitutes for an operator grant (REQ-003; SC-003).
- Chat text is an explanation, not a proof or execution authority
  (`contracts/presentation.md`).
- No native embedded UI capability is invented (REQ-008; SC-008).

## Requirements and acceptance scenarios

### REQ-001

Provide a reproducible owned synthetic journey from install/discovery through analysis/plan/grant refusal/execute/verify/recovery/export.

**SC-001:** Given fresh owned roots and registered fixture instances, when either supported host follows the journey, then every step retains input/output/candidate receipts and synthetic versus actual-host domains stay explicit.

Verification: [procedure_full_journey](validation-plan.md); [T001](tasks.md). Obtained evidence: none.

### REQ-002

Explain decisions with input identity, conflicts/dependencies, conditional premises, unknowns, assurance and observation limits.

**SC-002:** Given all analyzer classification classes, when chat summaries are generated, then each statement agrees with typed results and unknown is not mislabeled independent.

Verification: [procedure_faithful_summary](validation-plan.md); [T002](tasks.md). Obtained evidence: none.

### REQ-003

Explain advisory order and exact missing authority before opt-in execution.

**SC-003:** Given a prepared plan with absent or invalid grant, when the developer requests execution, then the host explains refusal and operator scope without issuing a grant or treating host approval as sufficient.

Verification: [procedure_authority_journey](validation-plan.md); [T003](tasks.md). Obtained evidence: none.

### REQ-004

Display actual private-result/verifier state and interruption/recovery outcomes with evidence links.

**SC-004:** Given successful, failed, cancelled and recovered runs, when the result is presented, then unfinished states never appear successful and source promotion/code correctness is not implied.

Verification: [procedure_result_journey](validation-plan.md); [T004](tasks.md). Obtained evidence: none.

### REQ-005

Render an interaction graph with semantic labels, accessible legend and bounded node/edge input.

**SC-005:** Given conflict/dependency/conditional/unknown edges and malformed graphs, when graph generation runs, then labels and color-independent styles preserve semantics or malformed/oversize data refuse.

Verification: [procedure_interaction_graph](validation-plan.md); [T005](tasks.md). Obtained evidence: none.

### REQ-006

Export deterministic Markdown, SVG and standalone HTML from selected evidence with hashes and provenance.

**SC-006:** Given identical typed input and versioned formatter, when each export repeats, then bytes/order/IDs are stable and receipt binds source/output hashes plus limits.

Verification: [procedure_deterministic_export](validation-plan.md); [T006](tasks.md). Obtained evidence: none.

### REQ-007

Escape and bound untrusted source/evidence in every export without scripts, remote references or secret inclusion.

**SC-007:** Given HTML/SVG injection, unsafe URIs and overlarge content, when export validation runs, then active/remote content and arbitrary reads refuse or are inert escaped text; no network/telemetry occurs.

Verification: [procedure_export_security](validation-plan.md); [T007](tasks.md). Obtained evidence: none.

### REQ-008

Provide clear onboarding, diagnostics, raw-evidence access and unsupported-rendering explanations in both hosts.

**SC-008:** Given missing feature and image rendering unsupported by a host, when journey presentation is requested, then bounded fallback and actionable diagnosis are visible; no native embedded UI capability is invented.

Verification: [procedure_onboarding_fallback](validation-plan.md); [T008](tasks.md). Obtained evidence: none.

## Scientific boundaries and compatibility

Domain: Presentation of existing bounded typed results and selected owned evidence; output generation does not expand runtime authority or observation.

Hypothesis: Clear evidence-oriented presentation may help developers understand system potential; comprehension and usability need observations.

Existing AIM/runtime/grant/verifier contracts remain unchanged. Analysis and preparation are consultative; host permission never substitutes for operator grants. No source ref promotion, repository-code/hook execution, arbitrary network effects or new scientific guarantee. Existing M4 G4 NO-GO and independent M3/M3.5 gates remain in effect.

SDK/documentation, structural checks, synthetic controls, actual host observations and independent reproduction have separate evidence domains. Passing one does not establish the others or human approval. Public APIs are additive experimental proposals with migration/versioning review during implementation.

## Evidence and unresolved questions

Planned procedures are in validation-plan.md; `assurance.json` binds obtained evidence for SC-002 and SC-004 to SC-007 only. The packet records a proposed design, not a runtime acceptance result. Required decisions: technical contract/ADR adoption, exact host versions and installation scope, provider budget/source rights for capture, independent review and founder acceptance. See program.md in SPEC-039 and evaluation-protocol.md in SPEC-044.

Open questions: OQ-1 to OQ-7.

- OQ-1: Does the owner reopen T001, T003 and T008 by running the sessions in the
  reopen criteria of the 2026-10-31 decision (T001: one session or an owned synthetic
  journey covering install to export; T003: an observed plan session that explains
  order and missing authority; T008: both hosts showing onboarding, diagnostics,
  raw-evidence access and rendering fallback)? Owner: founder.
- OQ-2: Does the owner accept the synthetic journey of #1161
  (`examples/journey/run_journey.py`) as the "owned synthetic journey" route for T001,
  so that `evidence/sc-001.json` can be bound? T001 records the owner reopen decision
  as pending. Owner: founder.
- OQ-3: When is the consumed-contract review recorded (CHK-007) and ADR 0021, which
  is Proposed, adopted? Owner: founder.
- OQ-4: Are exact host versions, installation scope and provider budget or source
  rights for capture still needed, given that the SPEC-044 registered evaluation was
  cancelled on 2026-11-01 and the plan lists them before capture? Owner: founder.
- OQ-5: Who performs the independent technical review that T010 requires, and on which
  frozen candidate? Owner: founder.
- OQ-6: Should `evidence/technical-clauses.json` and `evidence/technical-validation.json`
  (T011–T014) be bound as obtained evidence in `assurance.json`? None of the
  scenarios of REQ-001, REQ-003 and REQ-008 shows any today, and T011–T013 say
  original acceptance stays separate. Owner: founder.
- OQ-7: Which numeric limits apply to node, edge, input and output size, that
  REQ-005 and REQ-007 name? Owner: founder.

## Additive SPEC-047 boundary — current local candidate

The requirements/scenarios above retain their original criteria and evidence identities. [SPEC-047](../047-local-technical-telemetry/spec.md) owns default-off local numeric telemetry at the portable MCP and two analyzer CLI boundaries. Installation consent and reports are documented in [the telemetry guide](../../docs/tooling/TELEMETRY.md); five skills do not enable or collect telemetry. The [complete M4.5 map](../../docs/tooling/M45_ALIGNMENT.md) separates technical, observation, review and acceptance dependencies. Product metrics are not full evidence, experimental/training inputs or native/cost acceptance. Historical SPEC-044/T004 stays bounded-complete for 482fbcc. SPEC-044 T017 and T018, the disposition and admission of the new candidate, were cancelled by the [2026-11-01 owner decision](../044-ai-tooling-evaluation/owner-decision-20261101-cancellation.md); no criterion is marked complete by that cancellation. No original criterion is relaxed or retrospectively rewritten by this extension.

## Non-functional requirements

No performance or availability requirement applies in this spec. Operational
constraints it states: bounded node/edge input (REQ-005), deterministic bytes, order
and IDs (REQ-006), bounded and offline exports (REQ-007). No numeric bound is
stated: see OQ-7.

## Security and privacy

- Exports contain no scripts, remote references or secrets, and untrusted source and
  evidence are escaped and bounded: see REQ-007.
- Export validation involves no network or telemetry, and arbitrary reads refuse or
  are inert escaped text: see SC-007.
- Host approval is not treated as an operator grant: see REQ-003.
- Telemetry consent, reports and exchange belong to
  [SPEC-047](../047-local-technical-telemetry/spec.md); full evidence exports stay
  separate from them.

## Terminology

Shared terms follow the root `TERMINOLOGY.md`. Glossary of terms this spec uses:

- Journey: the ordered steps of `contracts/presentation.md` from install/discovery
  to export (REQ-001).
- Synthetic versus actual-host domain: evidence from an owned fixture versus from a
  real host session; the two stay explicit (REQ-001).
- Interaction graph: nodes that identify operations and edges that carry a kind
  (REQ-005, `contracts/presentation.md`).
- Export receipt: the record that binds source hashes, formatter version, output
  hashes and limits (REQ-006; `contracts/presentation.md`).
- Observational native receipt: a derived, redacted receipt from the owner's real
  host sessions; it does not replace the preregistered procedures
  (`validation-plan.md`, amendment 2026-10-31).
- Deferred: a task parked by the 2026-10-31 owner decision with reopen criteria.

Values named in this spec:

- Host: Codex, Claude Code (`assurance.json` `compatibility`).
- Edge kind: dependency, observed conflict, conditional premise, unknown
  (`contracts/presentation.md`; REQ-005 names conflict, dependency, conditional and
  unknown). Unknown means unresolved.
- Fixture case: independent-candidate, conflicting, conditional, unknown
  (`contracts/presentation.md`). The analyzer classification classes in REQ-002 are
  defined by the analyzer contracts, not by this spec.
- Run state: successful, failed, cancelled, recovered (REQ-004).
- Export format: Markdown, SVG, standalone HTML (REQ-006).
- Evidence domain: SDK/documentation, structural checks, synthetic controls, actual
  host observations, independent reproduction (Scientific boundaries section).

## Risks

- Risk: a chat summary diverges from the typed result, for example by labeling an
  unknown as independent (REQ-002, T002).
- Risk: a reader takes chat text as proof or as authority to execute (REQ-003, T003).
- Risk: an unfinished run appears successful (REQ-004, T004).
- Risk: untrusted source or evidence injects active or remote content into an export
  (REQ-007, T007).
- Risk: a host cannot render the image, so the journey is shown through the fallback
  only (REQ-008, T008).
- Risk: observational receipts do not cover T001, T003 and T008, so those tasks stay
  Deferred (T001, T003, T008).
- Risk: the hypothesis that clear presentation helps developers understand the system
  fails or cannot be tested without observations (T010).

## Assumptions

Taken from `assurance.json` `assumptions` and plan.md:

- Assumption: the roots used are owned, trusted local roots (SC-001).
- Assumption: contracts the journey consumes are reviewed separately (T001).
- Assumption: exact host, source and cost decisions are made separately before any
  capture (plan.md).
- Assumption: host and tool permissions are explicit (plan.md).

Not assumed: universal compatibility, positive utility and an available provider
budget. Hypothesis: clear evidence-oriented presentation may help developers
understand system potential; comprehension and usability need observations.

## Exit criteria

Verification is complete when each procedure of the [validation plan](validation-plan.md)
has obtained evidence recorded against its task in [tasks.md](tasks.md): procedure_full_journey
(T001), procedure_faithful_summary (T002), procedure_authority_journey (T003),
procedure_result_journey (T004), procedure_interaction_graph (T005),
procedure_deterministic_export (T006), procedure_export_security (T007) and
procedure_onboarding_fallback (T008). Evidence lives in `evidence/sc-00N.json`, bound
in `assurance.json` `obtained_evidence`; technical counterparts T011–T014 are in
`evidence/technical-clauses.json` and `evidence/technical-validation.json`.
Observational native receipts count only where they cover a task's levels. T009 binds
the quick and PR gates, and T010 closes the last task by recording the frozen
candidate, independent technical findings and the founder's actual decision; source
validation and hashes are not approval.
