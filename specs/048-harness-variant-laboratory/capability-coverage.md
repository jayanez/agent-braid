# Braid Harness capability coverage

Status: planning coverage audit, 2026-10-20. This replaces the original compact twenty-task scope. **Braid Harness** names Agent Braid's proposed capability and lifecycle. Harness2/Harness² names only the upstream reference and reused source provenance. No Google implementation, branding, operational assumptions or acceptance is implied.

The revised program has **3 milestones, 3 specs, 28 requirements/scenarios and 40 open implementation/gate tasks**: HAR.1 has 15, HAR.2 has 13, HAR.3 has 12. This count follows implementation ownership and independent acceptance; it is not a fixed completeness target. The original twenty tasks covered a first guidance/context pilot but compressed important implementation and left advanced capabilities without task ownership.

| Capability or lifecycle concern | Owning requirement(s) | Concrete task ownership / acceptance boundary |
|---|---|---|
| Task-local prompt/persona/procedure and rule precedence | 048/001; 050/001 | 048/T003; 050/T002: positive surface, immutable authority precedence, reject escaped paths and unsupported profiles |
| Strict immutable manifest, complete source/host/model/policy identity | 048/002 | 048/T002: independent consumers, full hashes, unknown provider identity and stale-cache refusal |
| Context inventory, retrieval, progressive disclosure and compaction | 048/009; 050/002/006 | 048/T011; 050/T003/T008: budgets, trust labels, omissions, fidelity and stale-fact controls |
| Memory and chronological reusable experience | 049/005; 050/006 | 049/T006; 050/T008: quarantine, scope, temporal prefix, contradictory/negative evidence, expiry/revocation |
| Tool guidance and executable deterministic helpers | 050/001/002 | 050/T004: typed allowlisted effects and qualified execution; no prompt-derived authority |
| Skills, trigger/frontmatter scaffolding and lazy workflows | 050/002 | 050/T003: dependency/reference validation, collisions, host compatibility and bounded loading |
| Delegated roles, handoffs and interaction-aware coordination | 050/004 | 050/T006: ownership/effect/dependency bindings, serial-reference correctness, cancel/resume and uncertainty |
| Hook/event and in-loop plugin components | 050/003 | 050/T005: per-host event schema/order/deduplication, effect limits, recursion-loop prevention and cleanup |
| Host task/method seams and actual Codex adapter | 048/003/004/006/010 | 048/T013 implementation; T008 independent Codex qualification; unavailable controls refuse |
| Host task/method seams and actual Claude adapter | 048/003/004/006/010 | 048/T014 implementation; T008 independent Claude qualification; neither host qualifies the other |
| Operator envelope, quotas, zero-new-spend and resource reservations | 048/003/007; 049/004 | 048/T001/T004; 049/T012: real enforceable limits, stage reservations, unknown cash and no paid fallback |
| OS/host containment and child/process settlement | 048/004 | 048/T005/T008: deterministic doubles versus actual native qualification, credential/network/filesystem boundaries |
| General/domain contrastive proposals and composition | 048/005 | 048/T006: invalid proposals, ties, missing observations, independent admission and keep-base |
| Sequential depth, parallel width and trial DAG/cache lineage | 050/005 | 050/T007: bounded search, retries, complete 4k/3k-style stage accounting adapted to actual policy, equal-budget comparisons |
| Base retention, anonymized comparison and abstention | 048/005; 049/009 | 048/T006; 049/T011: no adoption-by-output-presence; selection and outcome grading remain separate |
| Independent outcome verification, delayed grading and adjudication | 049/002/009 | 049/T011: oracle/proxy/human provenance, blinded rubric, disagreement and held-out leakage controls |
| Trajectories, artifact diffs and loss-aware observation | 048/010 | 048/T012: raw/normalized identity, missing events, bounded exports, secret inventory, retention and failed-attempt records |
| Durable completion, cancellation, interruption and recovery | 048/006 | 048/T007: real fixture kill points, no duplicate effects, drift refusal, exact attempt reconciliation and no authority renewal |
| Repository-derived synthetic and permissioned native corpora | 049/001/002 | 049/T001/T002/T004: C01–C04, eligibility/source yield, grouped holdout, temporal order and explicit native infeasibility |
| Continuity/recovery correctness and optimization | 049/003 | 049/T003/T005: task success, interventions, rework, duplicate effects, actual recovery and all attempted denominators |
| Coordination precision and useful parallelism | 049/003; 050/004 | 049/T003/T005; 050/T006: false-safe admissions, recall/coverage, missed safe parallelism, serial equivalence and full overhead |
| Complete costs, sensitivity and equal-budget comparisons | 049/004 | 049/T012/T005; 050/T007/T008: setup through cleanup, failed arms, tokens/quota/cash/human time, unknowns and marginal utility |
| Human promotion, profile registry and reversible transaction | 049/006/010 | 049/T013/T007: exact actual decision, atomic activation/rollback, stale and interrupted promotion controls |
| Future automatic promotion assessment and implementation | 049/007; 050/007 | 049/T008 assesses policy; 050/T009 implements disabled/shadow/canary/stop software; separate policy adoption before native activation |
| CLI codecs, errors, inspection and experimental workflow | 048/008; 049/008 | 048/T015/T010; 049/T009: strict versions, diffs, explicit action boundaries and existing CLI compatibility |
| Product-facing plugin/MCP advisory integration | 050/008 | 050/T010: separately versioned contract, explicit workspace/profile, bounded evidence and no silent execution extension |
| Installation, migration, drift, incident stop, rollback and uninstall | 050/008 | 050/T011: fresh/upgrade/downgrade/interrupted/unsupported-host controls, previous usable profile and privacy cleanup |
| License/provenance, review and final acceptance | All | 048/T001/T009/T010; 049/T010; 050/T001/T012: exact reused portions/notices, component and combined controls, scoped independent/human/founder review |

## Deliberate exclusions and reopen conditions

Benchmark downloads, cloud/provider bridges and bundled third-party runner patches are not dependencies for the selected owned-repository tasks. Reopen only if an admitted corpus needs them, after source/rights/cost review; the main Apache license does not cover every bundled asset. Model training and importing forecasting/System 1 acceptance are not needed for this harness program. Unrestricted global rewriting, authority/permission self-modification and arbitrary production-source mutation remain outside the contract rather than untracked promised capabilities.

Initial human promotion remains selected. Automatic promotion, executable components and native delegation have implementation ownership but cannot activate themselves. EUR 0 extra spend and native qualification remain gates, not optional warnings. Infeasible profiles leave the actual implementation/qualification task pending or receive explicit owner scope disposition; they do not disappear into a completed report.

## Closure rule

Every capability row must retain its requirement, implementation task, tests and obtained evidence or explicit pending/disposition record. Newly discovered supported mechanisms reopen this matrix and the owning plan; forty is not a ceiling. Completion of this document proves traceability only, not exhaustive source security review, implementation, utility or adoption.
