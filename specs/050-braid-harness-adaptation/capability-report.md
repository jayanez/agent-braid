# SPEC-050 capability report (T012)

Status: offline portfolio validation, 2026-11-12. This report separates three scopes for
every requirement:

- **Implemented**: code and tests are merged, and offline synthetic controls pass.
- **Qualified**: native, host, human or independent evidence supports the capability.
- **Activated**: the capability is enabled for ordinary use.

Nothing in SPEC-050 is qualified or activated. Every check behind this report is offline:
synthetic doubles in temporary directories, with no host, model, network, clock or paid
route, and no native run. The record is
[`evidence/t012.json`](evidence/t012.json), and the combined run is under
[`evidence/integration/`](evidence/integration/).

**No completeness claim and no product-utility claim.** This report does not claim that
the portfolio is complete, safe in native use, useful, economical or ready for adoption.
A passing offline control is deterministic engineering evidence only. It is not
qualification, activation, utility evidence or product acceptance.

## Combined offline validation

`tests/test_harness_integration_portfolio.py` (10 tests) runs the modules together with the
SPEC-049/T013 profile registry. One end-to-end path links them: component profiles; skills, tools and hooks on doubles;
orchestration against a serial reference; equal-budget search; curated retrieval; T009
production abstention; shadow and canary through the T011 lifecycle; incident stop with
registry rollback; one revocation reaching both the registry and the curation store;
human rollback; T010 advisory views over the stored records; uninstall; and recover.

The test asserts these invariants across the modules:

- Every kept record carries `executionAuthorization` (and `nativeExecution`) false, checked
  per record.
- No automatic-promotion run or lifecycle state reaches `active`. Lifecycle status keeps
  activation, ordinary use and export closed, and `activate` always refuses. The synthetic
  T013 registry does serve a decided profile until the revocation clears it; that pointer
  is registry data, not an activation.
- One revocation reaches the persisted registry and the curation store together.
- Every Python-level mutating filesystem call stays inside the workspace. A guard resolves
  each path when the call happens; an outside sentinel is also checked. Native code is not
  observed.
- A private payload never appears in a kept record or in any lifecycle-owned file other
  than its own private blob; only its hash is reported.
- Synthetic equal-budget accounting is deterministic. Repeated runs give identical
  comparison hashes, no arm exceeds the equal probe budget and search volume is not scored.
  The configured cash cap constant is EUR 0. No real cost was measured.

Adversarial controls cover tampered profiles and stored blobs, stale or skipped versions, a
future state format, identity drift, forged plans, contracts, policies, run states and
lifecycle state, automatic operators and blocked profiles. Each one refuses.

Cross-host checks: `claude` is the only supported host and is unqualified, and `codex` is
refused by the component compiler, the lifecycle and the hook matrix. Recovery checks:
interrupted install and uninstall are recovered without residue.

A counterfactual pass removed 27 guards (or named pairs), one at a time, across the
lifecycle, automatic-promotion, orchestration, component, tool, hook, curation and advisory
modules. The integration tests failed for 25. The two survivors each remove one of two
redundant checks, and removing both checks of each pair is detected. The per-guard results
are in the integration record. All 43 harness test modules pass (1808 tests, 3 skipped) under Python
3.13. The per-module counts are in the integration record.

## Per-requirement status

The table states the delivery evidence for each requirement. The PR numbers point to the
merged code. Only T009, T011 and T012 wrote task evidence files; for the other tasks, the
CI on the PR head is the `pr`-profile evidence.

| Requirement / scenario | Delivering tasks and evidence | Implemented (offline) | Qualified | Activated | Pending and owner |
|---|---|---|---|---|---|
| REQ-001 / SC-001 bounded component profiles | T001 contract (#1210); T002 `harness_components` (#1271); T003-T006, T010, T011 consumers; [integration](evidence/integration/) | Yes. Immutable profiles, linked versions, protected precedence, claude-only host schema, derived admission. | No | No | Native host qualification (SPEC-048/T008); C3-C8 admission stays blocked per contract section 8 |
| REQ-002 / SC-002 skills and qualified helpers | T003 `harness_skills` (#1273); T004 `harness_tools`, partial (#1272); T008 | Partial. Lazy inert skills and offline E0-E2 helpers only. No subprocess or network adapter. | No | No | T004 subprocess/network adapters wait for SPEC-048/T008 and an adopted E3 contract; contract section 8 C5 row amendment |
| REQ-003 / SC-003 hooks and plugin components | T005 `harness_hooks` (#1277); T011 | Yes, on doubles only. Event matrices are modeled, not observed. | No | No | Host hook inventory (contract section 12 Q3); containment qualification; C6/C7 blocked from the start (owner decision 4) |
| REQ-004 / SC-004 interaction-aware delegation | T006 `harness_orchestration` (#1278); T007 | Yes, as a serial policy layer with width 1. Advisory parallelism only. | No | No | Provider-native delegation needs its own qualified profile; C8 blocked |
| REQ-005 / SC-005 depth/width refinement | T007 `harness_search` (#1293) | Yes. Equal-budget arms on synthetic doubles. Depth or width above 1/1 needs a contract amendment. | No | No | Native concurrency (exact effect profile); any utility comparison needs native cohorts (SPEC-049/T014) |
| REQ-006 / SC-006 curation under drift | T003; T008 `harness_curation` (#1275); T011 | Yes. The held-out temporal comparison is synthetic, with caller-declared families. | No | No | Held-out native families (SPEC-049/T014); retention duration decision (contract sections 10 and 12) |
| REQ-007 / SC-007 governed automatic promotion | T009 `harness_auto_promotion` (#1312, [t009.json](evidence/t009.json)); T011 lifecycle canary and stops; SPEC-049/T008 `deferred` | Yes, disabled by default. The production policy abstains with `pending-endpoints` (rule 12). | No | No | Owner decision on pending endpoints; a separately adopted policy, ADR and operator decision for any activation |
| REQ-008 / SC-008 opt-in product capability | T010 `harness_advisory`, partial (#1292); T011 `harness_lifecycle` (#1317, [t011.json](evidence/t011.json)); T002, T004-T006 and T009 as consumers | Partial. A read-only advisory module CLI and an offline lifecycle library. | No | No | T010 top-level alias (owner decision, change to pinned `tests/test_harness_cli.py`, SPEC-049 re-freeze); plugin/MCP exposure is excluded here (M4.8); `evidence/t010.json`; human workflow usability observation |

## Held-out per-axis regressions

The only per-axis held-out result that exists is the SPEC-049/T005 deterministic
synthetic-control cohort
([record](../049-harness-evaluation-learning/evidence/evaluation/deterministic-cohort-20261112.json)).
T012 checked that the record's input hashes still match the tree, and the 19 controls in
`tests/test_harness_t005_cohort.py` recompute the recorded result:

- Continuity, 1 unit: A 0/1, B 1/1, C 0/1.
- Coordination, 4 units: A 3/4, B 3/4 (1 not completed: interrupted by stop-on-drift),
  C 3/4.

The record labels these rows descriptive-only, verdict-ineligible and plumbing only. Arm C
equals arm A by construction, and the oracles are not independent of the double. **No
regression or improvement verdict follows from them.** The native cohort, a non-trivial
arm C, the library ablation and the endpoints the double cannot compute are pending under
SPEC-049/T014. Per-axis dispositions are pending under SPEC-049/T010.

## Source and license deltas

Pinned upstream: `google-research/harness2` at `1cfe254e8d25b15f37048c3730134686abe60335`,
Apache-2.0 ([`LICENSES/Harness2-Apache-2.0.txt`](../../LICENSES/Harness2-Apache-2.0.txt),
[`docs/development/THIRD_PARTY.md`](../../docs/development/THIRD_PARTY.md)).

| SPEC-050 module | Recorded source use |
|---|---|
| `harness_search.py` (T007) | Apache-2.0 adapted file. Its header and `_PROVENANCE` name `core/recursion.py` (run_sequential/run_parallel), `core/selection.py` (base-inclusive pool) and `core/ledger.py` (reservation identity), with changes listed. |
| `harness_skills.py` (T003) | Original implementation, AGPL-3.0-only. It uses concepts only of `core/tree.py`, and no upstream bytes. This deviates from the acceptance word "Adapt" in T003. |
| `harness_hooks.py` (T005) | Original, AGPL-3.0-only. No upstream bytes, although T005's acceptance says "Adapt applicable hook/schema validation"; the same deviation as T003. |
| `harness_components`, `_tools`, `_orchestration`, `_curation`, `_auto_promotion`, `_lifecycle`, `_advisory` | Original, AGPL-3.0-only. No third-party source is recorded. |

Delta to resolve: the THIRD_PARTY.md section on Braid Harness names only the SPEC-048
seams (`harness_manifest`, `harness_surface`, `harness_admission`). It defers the rest to
"each module identifies its actual adaptation", so it does not list `harness_search.py`.
This report records that gap. It does not edit the file. `NOTICE` describes the harness2
adaptation generically, which is consistent with both.

## Review scope

The pre-PR adversarial, counterfactual, functional, quality and simplification reviews of
T012 were Claude subagent or local passes. They are not independent Luna review, human
review or founder approval. None of the three has been obtained for the portfolio. Each
needs separate authorization and its own record (SPEC-049/T010).

## Pending, by owner

- **Founder or owner decisions:**
  - tolerating pending endpoints (T009);
  - the T010 top-level alias;
  - retention duration;
  - any activation policy, ADR and operator decision.
- **T010 (partial):**
  - top-level alias;
  - `evidence/t010.json`;
  - the plugin/MCP surface, which is M4.8 and excluded from this task.
- **T004 (partial):** subprocess and network helper adapters (SPEC-048/T008 plus an
  adopted E3 effect contract), and `evidence/t004.json`.
- **Contract amendments:** the section 8 C5 row (T004); the host hook inventory (section 12
  Q3); the `core/prompts.py` pinned hash and `core/proposer.py` fit review (section 12 Q4).
- **SPEC-049:**
  - T008 is `deferred` and SPEC-050/T009 abstains with `pending-endpoints`, so automatic
    promotion stays disabled;
  - T004 native-pilot admission, a prerequisite of T014;
  - T014 native cohort, non-trivial arm C and library ablation;
  - T010 per-axis dispositions and review.
- **SPEC-048/T008:** native Claude qualification. Codex is not installed.
- **Human:** workflow usability observation (T011) and host requalification of any
  profile.
- **Review:** independent Luna review, human review and founder approval of the
  portfolio.
- **Provenance:** list the `harness_search.py` adaptation in THIRD_PARTY.md.
- **CI:** a stable `pr`-profile result recorded in the pull request.
