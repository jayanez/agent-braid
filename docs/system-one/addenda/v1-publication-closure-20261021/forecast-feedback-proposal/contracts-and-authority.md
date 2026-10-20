# Proposed contracts and route authority

## Separate contracts

The private ledger is a new research/evaluation contract, proposed schema `agent-braid-owned-work-evaluation/v1`, outside SPEC-047's store and current forecasting API. This name is a proposal, not an existing accepted schema. Review the required source/ADR/spec extension before collection. Existing `agent-braid-forecast-telemetry-v1` always declares `authentic-on-synthetic`; retain its bytes and frozen receipts. Real-repository records need a new explicit source kind and source-admission decision, never a renamed old receipt.

Ledger lineage: scoped opaque run/task/attempt/episode IDs; exact code revision, dirty-diff digest when applicable, config/model/policy/schema/tool versions, artifact and oracle digests. Hashes can identify private work and are not anonymization. No prompt text, code bodies, credentials, private histories, account identifiers, personal/team identifiers or ambient provider calls. A model field is unavailable/not-used when no model ran; it is not authorization to load one. Map joins locally inside the admitted ledger only, with private mapping separation and retention. Never export these keys into SPEC-047.

A prediction is immutable before the outcome: prediction origin, feature availability times/provenance and missingness, version/horizon/units, declared domain, baseline, prediction/interval or explicit not-produced reason. Reject post-origin features and outcome-derived predictors. Later outcomes append with maturity time, terminal state, verifier/source digest, oracle version and censoring reason. Record every attempt, including refused, cancelled, error, missing, selected-out and abandoned; denominator membership and exclusion reasons freeze prospectively. Agent-written success prose is not an oracle.

Monotonic local clocks describe wait, acquisition, decision, native preparation, transport, validation and cleanup separately, with parent/span IDs in the ledger only. Clock-domain mappings and uncertainty are explicit; nested/inclusive spans are not summed. Collect bounded CPU/wall, sampled RSS versus enforced memory limits, Git calls, retries, conflicts, validation failures and rework, with units and known/unknown boundaries. Observer overhead is a separate measured quantity; missing counters stay unknown. This does not recover SPEC-045/T007 historical complete costs.

Owned storage: owner-only external directory, no symlink/hardlink escape, bounded records/bytes, explicit append/flush and torn-write behavior, canonical digest chain and replay semantics, schema/version refusal, duplicate versus conflicting ID handling, consent/revocation and purge/backup limits. Initial proposed cap: 30 UTC dates, 10 MiB and 1,000 attempts; freeze exact caps before collection. No daemon/automatic upload. These are ledger proposal values, not changes to the existing collector. An incompatible ledger revision requires explicit migration/export policy; never silently convert aggregate SQLite or synthetic receipts.

Projection route: SPEC-047 receives only already-allowed numeric fields, coarse buckets and fixed enums, if that specific route has consent and admission. No arbitrary metadata traversal, extra columns, event rows, precise time, digest or persistent join IDs. A ledger failure may mark evaluation incomplete but must not mutate the decision, reset its budget, suppress refusal, grant execution or delay cleanup. Aggregate collector faults retain original noninterference semantics. Model/policy/version comparisons occur only within the ledger evaluation, never via identity tags in exported cells.

## Route matrix (must be completed before collection)

| Route | Current disposition | Required evidence / stop |
|---|---|---|
| Read-only design, generated numeric fixtures, schema/privacy negative controls | This documentary design is authorized; future software only within assigned scope | No live collection, models or network implied. Preserve fixture provenance. |
| Newly generated tasks on the owner's Agent Braid repo, deterministic observation ledger | Desired future scope, not yet an admitted real-source capture | Exact source roots/permissions, minimal feature allowlist, consent, caps, oracle and split protocol reviewed and pinned. Stop before collection if missing; this does not block independent schema/software preparation. |
| SPEC-047 collector/export on any route | Default off; existing privacy contract and route-specific admissions apply | No IDs/hashes or forecast internals. Existing SPEC-044/T018 and D18/E9 NO-GO remain controlling where applicable; do not enable by inference. |
| Existing native/provider pilot, private histories/accounts, authentic provider observation | Existing NO-GO/unavailable or excluded | Do not read prompts/credentials, launch account/provider calls or borrow budgets. Requires its own exact admission; no generic consent substitutes. |
| Deterministic new owned software traces outside that provider/native pilot | Evaluate applicability separately | Do not blanket-apply provider NO-GO to unrelated consented deterministic work; prove distinct source, boundary and authority first. |
| Real Codex/Claude host/model execution | Separate endpoint, cost, host and route gates | Zero-cost route verified; no model or activation permission from this plan. |
| Fitting/calibration, training-data admission, auto-promotion | Not authorized | Draft counterexamples/tasks only. No fit, threshold tuning, automatic model/policy change or training corpus admission. |

## Proposed REQ/SC pairs (supplement namespace)

- REQ-CI-001 / SC-CI-001: Route/consent ledger distinguishes allowed deterministic work from denied pilot; missing/mismatched authority refuses capture without disabling schema design.
- REQ-CI-002 / SC-CI-002: Versioned real-work contract preserves synthetic and SPEC-047 schemas; attempted sourceKind relabel or identity injection refuses.
- REQ-CI-003 / SC-CI-003: Private bounded lineage is immutable/replayable; wrong revision, ID reuse with changed bytes, torn writes, symlink, size overflow and expired data are handled without silent loss or privacy export.
- REQ-CI-004 / SC-CI-004: Causal feature/time/resource accounting; clock regression, cross-clock subtraction and post-origin feature use refuse or mark unavailable; nested cost not double counted.
- REQ-CI-005 / SC-CI-005: Auditable mature oracle/all-attempt registry; unknown/cancel/refused/censored stay visible; prose-only or post-hoc success labels cannot become gold.
- REQ-CI-006 / SC-CI-006: Frozen temporal/family evaluation; duplicated families/late features refuse split admission, coverage and undefined metrics are explicit; no fitting/calibration performed.
- REQ-CI-007 / SC-CI-007: Feedback produces provenance-bound counterexamples and task drafts only; attempts to grant/train/admit/promote/activate refuse.
- REQ-CI-008 / SC-CI-008: Privacy projection/noninterference and complete handoff; extra identity/time/content fields rejected, disabled collection does zero persistence and collector faults do not change product outcome/budget/cleanup.

These supplementary IDs are proposed under SPEC-045 except privacy compatibility references under SPEC-047. They do not override existing requirements or refresh assurance snapshots. Human/scientific review is pending.

## Existing permissioned windows and actual v1 coverage

`forecast_data.validate_window` already accepts synthetic and permissioned windows; the permissioned branch requires a source_verifier returning True. Reuse its availability/cutoff/observedMask, partition/transform/resource digests and causal checks. Parseability is not source admission. Version only the missing observation-ledger/TelemetryRecorder route; do not replace the forecasting system or add repository inputs to its current API.

Typed decision v1 requires flat names matching `[a-z0-9][a-z0-9.-]*\.txt`, two to four operations named from a/b/c/d. Real repository Python/Markdown paths and nested source trees fall outside it. Successful SDK/Codex fixtures do not establish general development readiness. Count supported, unsupported, refused, cancelled, unknown and legacy-analyzer-only tasks against the prospectively selected real backlog from its first task. Never rename/copy real files into .txt to claim actual coverage. A materially transformed fixture is a separate synthetic lane.

REQ-CI-009 / SC-CI-009: Original backlog/path/domain provenance is preserved; unsupported .py/.md/subdirectory and operation-count tasks remain in all-task denominators, with stage/reason. A versioned domain-extension proposal with new tests and separate authority is the result if coverage is infeasible; existing v1 regex/pins and refusal controls remain unchanged. Legacy analyzers may retain their already authorized uses, but their successes are not attributed to typed v1.
