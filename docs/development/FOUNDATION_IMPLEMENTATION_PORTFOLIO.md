# Foundational review and implementation portfolio

## Audit boundary and result

Started 2026-10-05 against public `develop` commit `f1bc304827b26c2cc3e02d5488ff2f82daa5453d`; packaged 2026-10-06. [The source inventory](foundation-review-inventory.json) binds baseline document/contract bytes. This is a repository-content and implementation-coverage review, not a refreshed literature/market review, independent reproduction or founder scientific approval. Provider versions and sources must be rechecked in their implementation tasks.

The original shared checkout was clean but behind public `develop`; its Spec Kit preflight rejected unreachable Git objects. Work resumed in an independent full clone with the exact reviewed SPEC-012 history restored to a local ref. The original object store was preserved. The independent clone passed the complete Spec Kit preflight before edits.

The foundation already supports a bounded analyzer, Git laboratory, structured-exchange model and experimental private runtime. It does not justify duplicating those implementations or treating candidate technologies as adopted. Six new draft packages cover actual gaps: 38 requirements, 40 acceptance scenarios and 44 prospective tasks. SPEC-019 gains two offline-preparation tasks. The tracking source contains 27 specs, 205 tasks and 12 milestones, including three new capability milestones. Each active commitment now has an existing implementation, an executable implementation/research task or an explicit contract/decision prerequisite. Optional rejected/watch choices can end without adoption.

## Finding register

Locations below refer to the baseline commit. Current-facing corrections do not rewrite frozen evidence or prior decisions.

| ID | Severity | Location / authority | Finding and disposition |
|---|---|---|---|
| FND-001 | High | `README.md:44–67,223–235,305–314`; Articles 13/14/20 | Product map and evidence status lag the implemented private runtime. Correct the command/product/status descriptions and expose current SPEC-021 G4 NO-GO. |
| FND-002 | High | `SECURITY.md:3–5`; Articles 6/12; ADRs 0019/0020 | Pre-implementation wording hides the bounded runtime trust boundary. Correct status, trusted components and excluded capabilities; make no production claim. |
| FND-003 | High | Article 15; SPEC-011 tasks; `agent_braid/mcp_runtime.py` | Outbound MCP runtime is not inbound recorded-effect ingestion. SPEC-023 specifies read-only generic/approval/async evidence mapping and conservative unknown handling. |
| FND-004 | Medium | SPEC-021 G4 decision; Article 19; H5 | No post-NO-GO full-cost follow-up exists. SPEC-022 diagnoses cost and registers bounded comparison without rewriting NO-GO or requiring speedup. |
| FND-005 | Medium | `RESEARCH.md` H2; Articles 5/9/19 | Non-Git effectful families and useful semantic-overlap comparison lack an executable protocol. SPEC-024 supplies simulated failure/effect/nondeterminism controls and a bounded H2 assessment, not real adapter admission. |
| FND-006 | Medium | Operational semantics T1/T2; Articles 4/8/10/17/23 | Contextual/trace-safety and proof obligations remain sketches or exclusions. SPEC-025 supplies bounded continuation checks, exact premises, proof review and comparator feasibility. |
| FND-007 | Medium | SPEC-019 T001/T007/T002; ADR 0018 | Real-source/label gates are explicit but offline preparation lacks a separate next task. T009/T010 and the readiness map make it executable without fitting, data admission or benefit claims. |
| FND-008 | Medium | Market validation priorities; community metrics; Article 21 | Proxy arithmetic and metric vocabulary are not operational adoption evidence. SPEC-026 supplies local measurement/intake tools and gated study/communication decisions. |
| FND-009 | Medium | ADRs 0014/0019/0020; Articles 6/12/20 | Source promotion, code isolation and external writes lack next refinement tasks. SPEC-027 supplies contract assessments and capability-specific GO/NO-GO decisions; separate adoption remains required. |
| FND-010 | Medium | `research/benchmarks/README.md:7`; claim discipline | Blanket absence-of-benchmarks statement is stale. Replace with obtained Git measurements and distinguish absent adaptive-agent/H5 evidence. |
| FND-011 | Low | `specs/019-native-predictor/research.md:29`; capture/report | Synthetic exclusion count says four rather than five across six sessions. Correct current research prose; zero real admitted pairs remains unchanged. |
| FND-012 | Medium | SPEC-002 T006, SPEC-009 T009 and SPEC-011 T008 | Later milestone/cutover records do not automatically close historically scoped tasks or approve the registry. SPEC-026 schedules evidence-backed current reconciliation; preserve original checkboxes until that decision. |
| FND-013 | Low | Assurance compatibility, Git replay and scientific integration pages | Adopted Article 13, M2 internal closure and separate runtime scope are described ambiguously. Correct editorial status/links only; record changed authority hashes in new drafts and preserve existing historical approvals. |

No constitutional MUST contradiction was found in the reviewed current semantic/ADR boundaries. That bounded review conclusion is not proof of completeness or scientific truth. Unimplemented obligations remain visible as work.

## Constitutional coverage and existing work

| Articles / obligation | Established bounded coverage | Next implementation / decision |
|---|---|---|
| 0, 13, 17, 18 — claims and evidence | Claim discipline, assurance dimensions, frozen records and negative controls | Every package retains hypothesis/finite/formal distinctions; SPEC-025 proof review and SPEC-026 intake |
| 1, 3, 7, 20, 24 — portable objects and distinct stages | Terminology, integer/AIM models, analyzer and separate runtime policy | SPEC-023 recorded-trace mapping; SPEC-027 expanded capability refinements |
| 2, 4, 6, 12 — order, confluence and execution premises | Finite lab, Git replays and verified private-runtime domains | SPEC-024 effectful simulations; SPEC-025 continuation obligations; SPEC-027 isolation/contracts |
| 5, 9 — effects, failures and counterexamples | Integer/Git/anchored controls; reducer/POR and synthetic M3.5 capture | SPEC-024 alias/version/duplicate/partial-failure cases and bounded H2 comparison |
| 8, 10, 11 — typed exchange and braid semantics | SPEC-018 anchored model with explicit conventions and finite limits | SPEC-025 premise/proof review and separate typed-domain expansion decisions |
| 14, 15, 16 — inspectable reports and tool metadata | AIM versions, reports, verifiers and bounded outbound MCP server | SPEC-023 inbound lifecycle/effect evidence; no vendor semantic fork |
| 19, 21 — useful workloads and differentiation | SPEC-013 real-Git evidence; SPEC-021 bounded utility NO-GO | SPEC-022 full-cost follow-up; SPEC-024 H2 protocol; SPEC-026 adoption evidence |
| 22, 23, 25 — independent research/engineering feedback | Modular lab, M3 model, research hypotheses and source registry | SPEC-025 named proof/comparator feasibility; SPEC-019 gated predictor; optional tools need decisions |

Existing SPEC-001–021 and milestones M0–M3 keep their recorded scope and status. New work does not re-close a milestone or promote evidence into another domain.

## Implementation sequence and capability exits

| Priority | Package / next task | Outputs and dependency boundary |
|---|---|---|
| P0 | Current-facing corrections and this audit | Accurate status, coverage inventory and preserved history; delivered by this documentation PR |
| P1 | [SPEC-022](../../specs/022-m4-utility-followup/spec.md), T001 | Reviewed full-cost protocol and allowed optimization boundary; existing runtime only; no dependency on M3.5 |
| P1 | [SPEC-023](../../specs/023-recorded-trace-adapters/spec.md), T001 | Portable offline trace fixture/mapping baseline; no dependency on M4 speedup or predictor data |
| P1 | [SPEC-019 readiness](../../specs/019-native-predictor/implementation-readiness.md), T009/T010 | Metadata prerequisite report and synthetic interfaces; T001/T007 still gate fitting and actual data |
| P2 | [SPEC-024](../../specs/024-effectful-workload-lab/spec.md), T001 | Fixed simulated operation/observation contract, negative controls and H2 comparison; no real writes |
| P2 | [SPEC-025](../../specs/025-contextual-proof-obligations/spec.md), T001 | Contextual premise/claim register and proof obligations; finite-check completion does not require a positive theorem |
| P2 | [SPEC-026](../../specs/026-adoption-evidence-program/spec.md), T001 | Deduplicated metric/intake protocol; no outreach, sensitive-data collection or publication without authority |
| P2 | [SPEC-027](../../specs/027-runtime-refinement-contracts/spec.md), T001 | Refinement matrix, promotion/isolation/external contract assessments; later capability-specific adoption |

Tasks within each package define dependencies, target artifacts, verification commands and evidence. These dependencies do not authorize concurrent agents. Planned commands and filenames are future targets unless separately listed as obtained checks.

A2A, NeMo, OpenTelemetry, proof assistants, hosted services, governance expansion and license/package changes retain their optional/deferred status. SPEC-023/025/026/027 assign version/conformance/privacy, concrete-value, governance or refinement decisions before any new implementation. Decisions may be `watch`, `rejected` or `research-only` with a reconsideration condition. No automatic SDK installation, service purchase or inference from a weekly radar.

The existing 2026-09 adoption seed is historical and stays immutable. [The current follow-up map](../../research/adoption/2026-10-foundation-followup.md) identifies next work without pretending a stage transition or adoption decision occurred.

## Assurance, validation and delivery

All six new assurance records are drafts with human review pending and no obtained feature evidence. They bind the current authority inventory; the editorial changes to three authority pages are disclosed above. Existing historical authority/evidence snapshots and review records remain unchanged. Scenario references point to named prospective quickstart checks, not unrelated passing tests.

Structural validation, a successful PR and generated issues only establish repository/task consistency within their check boundaries. Scientific validation, model training, real-source rights, new execution authority, release publication and milestone acceptance remain separate.

Delivery uses source validation, the proportional quick/PR profiles, independent Luna document/domain review and a normal PR. After merge, GitHub reconciliation reviews exact operation/hash scope, runs guarded apply from clean `develop`, then checks for `operations: []`. Project membership and custom Review pending status require separate verification; an inaccessible Project is reported as a limitation.

The available GitHub CLI token lacks `read:project`; a read-only GraphQL attempt could not verify private Project membership/status. Browser discovery also found no available browser for this task. Repository issue/milestone reconciliation remains independently executable. No token scope, credential or Project state was changed to bypass this limitation.
