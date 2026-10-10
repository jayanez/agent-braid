# M4.5 implementation status and source map

## Current preparation scope — 2026-10-10

The active work is the [five-task preparation plan](../044-ai-tooling-evaluation/preparation-delivery-plan.md).
The existing implementation candidate was integrated with public `develop`
`526fa11c2a074abfe8c5c1217a4529a5f60ed4da` at
`aae3e0062d2b8be68ccf42a27c6950a2d3283047`; its Spec Kit preflight passed.
The source and installed checks described below are historical snapshots, not
validation of that integration or later preparation changes. Both target dependency closures and the verifier/recipe passed independent
technical review. Frozen source `3885706eeb64837c1b409d24a9b0754eb33301cd` passed
fresh offline macOS core/tooling installations and read-only CLI/MCP parity; a
hash-bound Linux input bundle is prepared with static refusal checks. See the
[preparation proof](../../docs/tooling/evidence/preparation-20261010.json).
Delivery requires final validation, evidence review, merge and remote tracking;
[PR #467](https://github.com/jayanez/agent-braid/pull/467) records the exact-head
integration and validation results separately from this artifact proof.
The complete evaluation and native-host acceptance remain separate gates.

## Historical implementation inventory

Status date: 2026-10-10. This is a source map for the proposed M4.5 implementation and closure work. It does not update task checkboxes, assurance records, approval state, or milestone state.

The earlier planning source map used `develop` at `59d0eadbea772dbff32fb9daca88bd39ab67a030` and later integrated metadata/evidence commit `7c10b248d34a05f15195376d72884d9b443fe36a`. The historically inspected source commit was `153c8fb7452fc55ddb50ad979ba8f872f9c1fb2d`; its identity is known. Approval and freeze of the prospective evaluation candidate remain pending. Neither source integration nor an earlier M4 decision establishes M4.5 acceptance. Code present in this candidate is not, by itself, paired scenario evidence, host observation, clean-room reproduction, approval, or task completion. The registered 60 child tasks and six parent tasks retain their existing acceptance criteria. SPEC-044 T003 alone is checked for 19 bounded deterministic controls on its historical candidate; the other 59 task checkboxes remain open. No later-candidate or host acceptance is inferred from that record. Do not create replacement task IDs or reduce the planned scope.

## Current integration and evaluation preparation

The current integration includes `develop` at
`42d99fa8eabb4295f8605e564bc0ea0fa6fc09e0`, including the separately approved
bounded M4 closure. That predecessor decision does not approve M4.5 or change
historical G4 NO-GO and negative-utility evidence.

The clean integration source is `153c8fb7452fc55ddb50ad979ba8f872f9c1fb2d`.
The reviewed installed-wheel observations use the earlier product candidate
`9dfdf27eb54fa6a912d8cae4b2a05b67fbb368be`; the recorded product module bytes
match the integration source. This is not a wheel built from the integration
commit. The [technical evidence status](../../docs/tooling/TECHNICAL_STATUS.md)
records that boundary and outstanding procedures.

The owner approved the subscription-only, EUR 0 additional-spend policy and
the observable model-route interpretation: use an exposed immutable identifier
when available, otherwise bind the exact selector, effort, CLI, catalog,
configuration and account route while declaring the backend unknown. The
SPEC-042 SC-008 clarification retains v1's supported local installation boundary.
These individual decisions do not approve the complete prospective evaluation
registration or authorize a cohort capture.

Candidate source now contains subscription-only admission and stop controls,
versioned model identity, registration-bound monetary accounting, and verified
composition of provider cash, allocated subscription cost and human time.
The EUR 25 accounting ceiling applies to provider cash plus subscription
allocation; the separate additional-cash ceiling remains EUR 0. Reviewer cash
and human time remain explicit rather than being inferred as free. Required
source verifiers are external trust boundaries, not production authenticators
supplied by the library. Offline report controls preserve incomplete evidence
and supported failures of registered outcome and safety criteria separately.
They do not perform human scoring or assert scientific utility.

Provider authorization and availability observations are retained privately.
They do not establish every attempt's route, authenticated cost sources or native
host acceptance. No M4.5 native cohort has started.
Before technical capture, the exact candidate still needs stable validation
receipts, fixture-rights approval, exact host/model builds, billing route/rates,
frozen candidate SHA and rubric, the mandatory v3 included-subscription policy,
an approved technical `fullCostScope`, the approved human-evaluation deferral,
the two abstract independent reviewer roles and all applicable owner/provider
approvals. Keep `humanReviewers` empty for this phase. Named human identities,
ratings/adjudication and reviewer fee/time applicability belong to the later
bound human addendum; they do not block technical preparation. Technical receipts
and aggregates still require complete registered coverage and trusted external
attestation. This status does not authorize capture or a provider call.

Private preparation records retain unavailable attempts and one previously
authorized inference outside the intended 108-attempt cohort. They are not
registered observations, skill-loading receipts or host-acceptance results.
Their incomplete discovery attempts do not establish that a model or host
feature is absent. Preparation does not prove every namespace's authentication,
actual isolation, native skill loading, cohort capture or capture authorization.

## State vocabulary

- **Code present** means an implementation path or deterministic control exists in the current candidate source.
- **Procedure/evidence pending** means the paired validation procedure has not produced an obtained receipt bound to the final candidate and required positive/negative controls.
- **External gate pending** means a required host, rights, provider, human, clean-room, review, founder, merge, or tracking action has not been established by this source map.
- **Observed predecessor context** means a dated report from another workstream. It is not current authorization or M4.5 evidence.

The implementation-status map does not convert any of these states into task completion. Existing `tasks.md` files remain authoritative for IDs, requirements, and acceptance criteria.

## Source map: W00–W16

| Work package | Existing stable task IDs | Candidate source and behavior present | Paired evidence and remaining boundary |
| --- | --- | --- | --- |
| W00 — program and dependency corrections | 039/T001–T007 | `program.md`, `analysis.md`, and SPEC-044 task/validation annotations retain the six-spec program and stable IDs; dependency notes distinguish accounting instrumentation from completed accounting, packet readiness from a founder decision, and the complete journey from its initial scaffold. | All 039 procedures and candidate-bound assurance are pending. No architecture adoption, founder decision, or tracking closure is implied. |
| W01 — optional SDK and protocol foundation | 040/T001–T002 | `pyproject.toml`, `agent_braid/tooling_mcp.py`, and `tests/test_tooling_mcp.py` contain the isolated optional MCP extra and SDK-backed server entry point; core imports remain separate from the optional SDK. | Installed core/extra behavior and both required protocol-version paths need paired package/protocol receipts. Preserve legacy behavior; no actual-host discovery is established. |
| W02 — operation surface, schema, roots and parity | 040/T003–T005 | `agent_braid/tooling_mcp.py` implements the experimental `analyze-work` surface, bounded inputs, result envelope and configured-root/mode handling. Existing CLI/runtime APIs remain the delegation boundary. | Full dereferenced CLI parity, malformed/deep/oversized input refusal, root containment, analysis-only advertisement and text/structured agreement require candidate-bound controls. |
| W03 — grant boundary and interruption | 040/T006–T007 | MCP execution/recovery delegates to existing runtime and grant policy; cancellation/concurrency paths and refusal/error mapping are represented in the adapter. | Exact grant, stale/expired/revoked/reused grant, cancellation, recoverability and no-false-success procedures remain pending. No new grant issuance route is authorized or exposed. |
| W04 — prompts and resources | 040/T008 | `agent_braid/tooling_mcp.py` contains bounded resource/inventory/chunk and read-only prompt support. | Resource ownership, three prompts, chunk reconstruction, hash/range/staleness negatives and large completed-result behavior need paired receipts. |
| W05 — canonical skills and analysis/plan | 041/T001–T003 | Five English canonical `SKILL.md` files are present in `integrations/agent-braid/skills/`. `agent_braid/tooling_assets.py` inventories names, versions, content and hashes from installed package resources, with explicit source-checkout loading. | Installed bundle discovery, full reference resolution, skill behavior, unknown/conflict disclosure and absence of authority claims still require validation. Skills do not confer permission. |
| W06 — execute and recover guidance | 041/T004–T005 | The canonical execute/recover skills describe use of existing grants, status/verification and current-state recovery. | Granted, ungranted, interrupted, stale and refusal journeys need adversarial paired controls; skill text is not runtime enforcement or a host receipt. |
| W07 — evidence, fallback and security guidance | 041/T006–T008 | The canonical evidence skill and supporting guidance cover provenance/limits, bounded read-only fallback and security refusals. | The final evidence guidance must be checked against the implemented formatter and adversarial fixtures. No generated Spec Kit skills are modified. |
| W08 — package assets and lifecycle API | 042/T001–T003 | `build_support.py`, `MANIFEST.in`, `agent_braid/tooling_assets.py`, `agent_braid/tooling_install.py`, and the `tooling` command group in `agent_braid/cli.py` provide package-resource wiring and lifecycle planning/apply entry points. | Wheel/sdist relocation and both hosts' actual configuration conventions, user/project scope and per-server roots require clean packaging and selected-host validation. |
| W09 — safe apply and doctor | 042/T004–T005 | `agent_braid/tooling_install.py` contains previewed transactions, ownership receipts, atomic file updates, backups, drift checks and read-only diagnostics. | Preservation, collision/concurrent-edit, rollback, idempotency, and separated doctor status procedures remain pending; no real host configuration has been changed by this status map. |
| W10 — owned update/removal and provenance | 042/T006–T008 | The lifecycle module includes receipt-scoped update/uninstall behavior and package/environment inventory. | Modified/shared residual reporting, relocation, interruption, dependency/license provenance and macOS/Linux reproduction require paired controls and separate clean environments. |
| W11 — journey explanation and basic presentation | 043/T001–T004 | `agent_braid/tooling_present.py` renders bounded summaries from result envelopes, preserving identity, classifications, status, provenance and observation limits. | The full install-to-export synthetic journey and actual private-result/verification/recovery scenarios are not evidenced by the module's presence. |
| W12 — interaction graph | 043/T005 | `agent_braid/tooling_present.py` builds a bounded graph with semantic edge types and a legend. | Accessible labels, semantic distinction, malformed/oversized inputs and no invented independence need paired controls. |
| W13 — deterministic exports and safety | 043/T006–T007 | `agent_braid/tooling_present.py` provides deterministic JSON/Markdown/SVG/HTML export helpers, escaping, bounds and selected evidence references. | Hash/provenance receipt, injection/secret/URI/active-content/remote-reference negatives and raw-evidence fidelity need validation. |
| W14 — onboarding and completed offline journey | 043/T008; completion evidence for 043/T001 and 041/T006 | `docs/tooling/README.md`, `docs/tooling/INSTALL.md`, `docs/tooling/JOURNEY.md`, `docs/ai-tooling-presentation.md`, and the presentation/skills modules provide onboarding, diagnostics, raw-evidence and unsupported-rendering guidance. Pinned fixtures include 12 Git runtime recipes and six AIM controls; explicit scenario preconditions distinguish granted execution and existing interrupted-run recovery. The materializer supplies neither context; private synthetic test-only operator controls exercise those paths separately. | `tests/test_tooling_journey.py` now exercises both isolated host asset formats, all five skill hashes, service discovery, analysis, preparation, missing-grant refusal, a separate test-operator grant, checkpoint interruption, inspection, independently granted recovery, expected-tree verification and deterministic export. It also preserves the source revision/tree. This is an owned offline engineering control; its paired final-candidate receipt and feature acceptance remain pending. W14 does not satisfy actual-host W18. |
| W15 — registration and accounting preparation | 044/T001; instrumentation prerequisite of 044/T006 | `agent_braid/tooling_evaluation.py` and `tests/test_tooling_evaluation.py` provide offline registration validation, exact 108-slot generation, immutable ledger history, full denominators, cost completeness, cap-stop checks and human-label eligibility controls. `agent_braid/tooling_capture.py`, its tests and `docs/tooling/CAPTURE.md` add hash-bound admission-only receipts: a fixed OS-account/registration store refuses alternate-root and concurrent duplicate admissions. Authentic decision/cost/stop attestation remains a trusted external verifier boundary; no production verifier is provided. Explicit host adapters and a bounded local process supervisor now have synthetic process controls; authentic live sources and actual host provenance remain pending. `agent_braid/tooling_fixtures.py` and `examples/tooling/` pin 18 owned synthetic definitions and six prompts: 12 Git runtime-request recipes for four runtime journey classes and six AIM requests with explicit unknown-coverage controls. Each fixture declares scenario preconditions, phases, outcomes, and context status. Installed loading targets package resources; source JSON requires explicit source-checkout mode. Offline tests also exercise one synthetic execute/status/verify path and one controlled interrupted-run inspect/resume/verify path with test-only private grants. | The minimal template is intentionally invalid for capture. The full `examples/tooling/registration-draft.json` binds the pinned 18 definitions/six prompts and supplies the separately approved numeric caps and proposed model names described in `docs/tooling/BUDGET.md`; provider opt-in remains false and approval, exact builds/rates and human identities remain pending. Materialization creates requests only: execute still needs an exact operator-supplied plan-bound grant; recovery also needs an existing interrupted-run state and matching recovery grant. The fixture helper does not create those contexts or perform runtime operations. Tests demonstrate local synthetic code paths only, not host sessions, captures, or approval. No candidate-specific approved registration, fixture-rights record, rates, reviewer record or capture exists. Numeric cap approval is recorded separately and does not approve these other decisions. Instrumentation validation must precede any future attempt; accounting completion follows all outcomes. |
| W16 — deterministic offline evaluation controls | 044/T003 | `tests/test_tooling_evaluation.py` exercises synthetic registration, roster, denominator, cost, cap, rating, authority, fidelity and adjudication controls without provider or host execution. | The already checked T003 is bound to its historical 19-control candidate. The current unit controls and private later-candidate receipts do not replace that canonical record, prove all product oracles, or establish real sessions or later-candidate acceptance. |

The candidate also contains CLI registration in `agent_braid/cli.py`, packaging resource hooks, and focused tests for assets, MCP, lifecycle, presentation, evaluation and fixtures. A repository quick-profile run completed with 837 tests, 3 failures and 6 skips; it is not a pass. The failures were in unchanged Git counterexample supervisor tests whose child Python resolved from PATH to system Python 3.9.6; a Luna reviewer reproduced the failures under that PATH and the supervisor suite passed all 9 tests when PATH selected the existing Python 3.13.11 environment. Preserve the failure/skip diagnostics. The first stable PR run was interrupted after hosted CI found an optional-SDK assumption in a new core-only test. The corrected test covers both environments without omitting its pin/refusal controls; the isolated SDK job remains mandatory. Hosted CI on superseded candidate `b3f5ce6ad4bbd2bd284b8d83a678b7975fa2cd16` passed 871 core tests with 7 skips and 24 mandatory isolated SDK tests. Its local PR profile was interrupted after an agent temporarily added untracked files; those files were preserved outside that candidate. Both interrupted profiles remain non-passing observations. The newer integrated candidate requires a fresh stable PR profile; earlier CI does not validate these later changes. This does not complete T009 or imply host, clean-room or acceptance evidence.

Capture preparation additionally contains `agent_braid/tooling_measurements.py`,
`tooling_host_events.py` and `tooling_sessions.py`, with focused controls and
bounded documentation in `docs/tooling/`. Local measurements retain sampled
process scope, logical private-disk scope and unknown provider/human costs.
One-shot event parsers enforce ordered starts/terminals and expected MCP server
sets, including an explicit empty set; caller-supplied streams do not prove real
host provenance or configured-but-unused Codex servers. The session coordinator
serializes dispatch across a registration, compares its durable ledger head,
requires fresh attested cost/stop inputs, and preserves interrupted/open attempts
without replay. Explicit host adapters now compose with bounded process
supervision and externally verified live cost/stop observations. Verified cost
reconciliation preserves revisions, actual/estimated monetary bases, unknowns
and non-additive peaks. The v3 report also requires an external technical-summary
attestation bound to the summary, registration, roster, approved scope and complete
technical receipt coverage before showing technical aggregates; no production
trust root is supplied. Decision/outcome authenticators and actual live sources
remain external; local stopping does not guarantee provider cancellation. These
components prepare W18/W19; no registered capture, attested technical summary or
full human-inclusive accounting is established here.


## Remaining waves and closure gates

| Work package | Existing stable task IDs | Status and required next evidence |
| --- | --- | --- |
| W17 — clean reproduction | 044/T004 | Pending. Produce distinct clean macOS arm64 and Linux x86_64 package/core/protocol receipts bound to the same supported candidate. Linux reproduction makes no Linux actual-host claim. |
| W18 — selected-host journeys | 044/T002 | Pending. Obtain actual Codex and Claude Code macOS arm64 discovery, all-five-skill loading and complete basic-journey receipts for the exact registered candidate. Prior legacy observations do not count. |
| W19 — 108-slot comparison and complete accounting | 044/T005–T006 | Pending. Requires approved registration and W18, pre-attempt budget/cost-stop admission, full intended roster, all outcomes and costs. Preserve not-started, failed, refused, cancelled and recovered rows; unavailable values remain unavailable. |
| W20 — technical interpretation and deferred human scoring | 044/T007 | Technical portion pending: preserve all 108 outcomes, denominators, technical cost availability and frozen rubric. Human identities, ratings, disagreements and adjudication are explicitly deferred under the approved v3 clarification; two abstract independent roles remain. Model review cannot replace later human ratings. |
| W21 — validation and reconciliation | T009 in 039–044 | Pending. Complete each paired procedure, run the explicit quick profile and one stable PR profile on the exact candidate, record skips/failures honestly, and bind results without implying host observation or approval. |
| W22 — frozen review and decision packet | 039/T008; 044/T008; T010 in 039–044 | Pending. Assemble candidate/evidence hashes, actual receipts, independent technical findings and a decision packet. Packet readiness requests a decision; it does not record one. Founder acceptance/rejection and scope decision remain explicit human actions. |
| W23 — governed merge and tracking closure | 039/T006 and 039/T008–T010; final parent/child/milestone dispositions | Pending. After accepted evidence and governed integration, reconcile exactly the existing 60 children, six parents and milestone 19; require an empty scoped audit and separately verify any private Project state. |

The earlier full technical-evaluation goal retained all technical work: five product skills, optional SDK behavior, installation/configuration, accounting and negative controls, registered clean reproduction, both native host journeys, all 108 intended attempts, technical interpretation and independent technical review. The two human outcome evaluations and their adjudication were explicitly outside that earlier goal and remain pending. The current five-task preparation goal is described above; the broader technical waves in this section remain open outside that immediate delivery scope. Unknown human fees and times are not zero. Founder acceptance, merge, governed tracking and formal milestone closure retain their separate approval and evidence boundaries; none is implied by completion of the technical goal.

## Predecessor context and evidence boundaries

The inspected predecessor chats were titled **“Planificar cierre de M3.5”** and **“Planificar cierre de M4”**. These are thread observations from the planning window and must be refreshed before sharing an environment or consuming changed evidence.

- The M3.5 thread reported PR #463 preparing metadata-only source/protocol review while source-family selection, specific inspection/capture rights, and human/scientific gates remained pending. M4.5 v1 uses registered owned synthetic fixtures; it does not inherit M3.5 source rights, payloads, predictor, or approval.
- The M4 thread reported PR #465 merged, 20/20 prospective captures, and a current Codex legacy six-tool check with zero model calls. It also reported the Claude launcher correction and CLI login as pending. These are predecessor observations only: they do not prove new MCP discovery, five-skill loading, actual M4.5 journeys, or any of the 108 registered arms. Refresh current state before capture.
- Historical predecessor observation before the separately approved 2026-10-09 closure: `23dbb8c` (PR #468) adds bounded Claude Code 2.1.285 observations on candidate `e66f9a1`: missing-grant refusal, a verified interrupted prefix, recovery/completion and suppressed consumed-grant retry. It records 14 observed turns against 20 reserved slots, with no cost measurement or Claude abort exercise. All six M4 exit rows remain open. This metadata is consumed as predecessor context only; it does not prove the new M4.5 MCP surface, five native skills, selected host builds or registered cohort.
- Keep whole-M4 acceptance and historical G4 NO-GO separate. The optional SDK remains additive and must preserve the legacy six-tool contract and core dependency behavior.

The candidate includes a one-shot process supervisor and explicit host adapters. Their tests execute owned synthetic subprocesses. The private preparation inference described above was outside the registered cohort; no cohort session or registered provider capture was run. The owner approved the numeric evaluation caps separately on 2026-10-08. This is not source-rights, provider, protocol or capture approval. The legacy evaluation registration draft retains false provider opt-in; model names remain recommendations. Before a technical attempt, resolve fixture rights, exact host/model builds, billing route/rates, frozen candidate SHA and rubric, mandatory v3 technical scope/deferral/roles, and all source/account/budget/permission approvals. Human identities and reviewer fee/time applicability remain deferred; they are not set to zero or treated as full economic completion. The eventual code candidate SHA must be the integrated/frozen commit, not the planning baseline or a local workspace path.

In synthetic offline report controls, the report preserves validated ledger attempt identifiers separately from intended slot identifiers. Missing-cost fields are attributed to per-attempt, setup or cohort scopes, retaining all intended slots and null actual identifiers for unstarted slots. Structured and narrative outputs retain this mapping while excluding free-form event text. These report controls do not authenticate costs or human ratings, approve a registration, assert utility, or complete any actual-host, human or founder gate.

## Candidate-bound autonomous technical results — 2026-10-10

The local procedures authorized by the bounded closure plan have produced canonical
scenario evidence. See [technical evidence status](../../docs/tooling/TECHNICAL_STATUS.md)
for the exact receipt map and limitations, and [autonomous completion](../../docs/tooling/AUTONOMOUS_COMPLETION.md)
for the proof inventory. The evidence spans distinct candidates: package checks on
`53f1704`, engineering tests on `aaae2e7`, and the final program/MCP/lifecycle
procedures on `5cffa9d`. No result is transferred across those candidates.

The paired technical run reports 8/8 program controls, 8/8 MCP scenarios and 37/37
MCP tests, 13/13 lifecycle tests, 223 engineering tests without skips, fresh
macOS wheel/core/tooling installation, and Linux AMD64 emulated installation.
The local MCP SDK peer is not a Codex or Claude host launch. The Linux run is not
native-hardware or performance evidence. The 108-attempt cohort has not started.

The original 60 task acceptance criteria remain unchanged. Nineteen auxiliary
evidence tasks add to that scope: current target 52 completed and 27 pending task
issues, plus six open parent issues. Native-host procedures, human review and
interpretation, founder acceptance, ADR adoption and milestone closure remain
external gates. M4's bounded-complete decision preserves historical G4 NO-GO and
negative utility; M3.5 remains independent with zero admitted real pairs.
