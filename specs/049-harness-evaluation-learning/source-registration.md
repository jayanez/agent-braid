# HAR.2 source registration — kickoff inventory

Status: inspected source inventory and proposed engineering sampling design;
`049/T001` acceptance remains pending. No HAR fixture was created or executed by
this registration; no native source was collected or admitted. Trace:
SPEC-049/T001, REQ-001/SC-001 and REQ-003/SC-003. Observed on 2026-10-21.

## Source identity and rights boundary

The inspected repository snapshot is `a6329c828011d1468fed3dfa4e98f5a8531167e2`
(`develop` after PR #655). [corpus.md](corpus.md) retains the earlier
`69e7d374e5aaf13376486664e7368711d9826e6f` provenance baseline; this document
adds a current readback rather than rebinding historical evidence or acceptance.
Git blob IDs and SHA-256 below identify the exact committed file bytes. Inspection
used bounded Git reads, Python AST inspection and byte hashing, without importing
or executing the inspected modules. No source test result is claimed here.

S01–S03 and S06 carry `AGPL-3.0-only` SPDX notices. S04–S05 are repository
specification documentation governed by the `CC-BY-SA-4.0` mapping in S00.
N01–N04 also carry `AGPL-3.0-only` notices. The repository license mapping and the
owner's authorization for this repository work are the basis for preparing owned
synthetic derivations; preserve applicable attribution, notices and modification
history when producing them. This is not an independent ownership audit or a
permission receipt for private/native task content. No upstream benchmark,
third-party dataset, provider transcript or personal task material is admitted.

| ID | Source path | Git blob | File SHA-256 |
|---|---|---|---|
| S00 | `LICENSE` | `e35c94d1e340046d033a4434fa684924ca1dae04` | `340d66a837b3a1617645d00622a46d1bcbf3534bedd997b6461d16d2e08b374f` |
| S01 | `tests/test_m4_alpha_scheduler.py` | `adeaf2227a088b19b9e59b92ac4324075a00181a` | `03966aac4af6dc9f4d99400aa0daf26bdb76711b8a50ce30d93ee60982f3ba52` |
| S02 | `tests/test_tooling_sessions.py` | `0b0c89bb92bc5b89f0ba5e3893c3e38de62d9bb5` | `17c80f57da18f7f0fc0d945a024496bbdd767d3e9555023248a769d38894fe33` |
| S03 | `tests/test_git_adapter.py` | `2951ca3348947a15925abe16fb6738b642de3bc0` | `f27408f851d23c78460bfc52b3ebc024ef58acde1c0d0f649dc9512d78b4c067` |
| S04 | `specs/028-system-one-core/decision-delivery/handoffs/DDP-T08.md` | `e8212f520d7d3ee8a2c88519d4d23b7b57e92687` | `fe7268efae5a539bff6435ba7575e2ee421437ff7e66943b337fc25437b46a6f` |
| S05 | `specs/028-system-one-core/decision-delivery/handoffs/coordinator.md` | `c25854a75fb3b8029f46a26f23f2af3048f62dd6` | `827b0ddafbb98f970426205307c39131161013ce85fcf6553501bd4974479bbd` |
| S06 | `tests/test_git_runtime.py` | `3241f4be4e3d0f43bfbee03852dfd62f058afda4` | `70e0655241bb64b4fb620309b0897c350b077a46db57be142f000a2e0d46fe47` |
| N01 | `research/owned_work_coverage.py` | `492681a0ba7aa82da626021800c165fbe60ab755` | `f398f0fc42e182ecf2b8e207d35a263a063d64650c84a8f6a23b699422ddf120` |
| N02 | `tests/test_owned_work_coverage.py` | `ee9211710865a73ff4b7ca404846257cf4b1e9b2` | `0dcfc9b60143ff137d8cd2bfb7fe204e50ceb585dfff887271022ee0ec92e417` |
| N03 | `tests/test_system_one_verified_components.py` | `0d5eb0c97cb38521b85424f315c3945762f78537` | `01abcb850572c3ad0f85beccaf7d437367fa388f681f0b77d55be24c98c32dcf` |
| N04 | `tests/test_system_one_verified_consumers.py` | `d2661bacf222ff88ec1e53dcc86494247d6bc6d8` | `d88c6dcb8f49a31023431258662cf82f3c848f1a92c3384ca0e74f430997493c` |

## Inspected anchors and expected observations

The inventory contains five direct case-source files (S01–S05), seven named test
methods and two handoff documents, plus shared fixture helper S06. These are
inspection counts, not independent cases, registered HAR attempts or trial yield.
Line ranges refer to the pinned snapshot.

| Family | Inspected anchors | Proposed engineering observation and limit |
|---|---|---|
| C01 — continuity | S01 `RuntimeSchedulerTests.test_fresh_process_kill_preserves_prefix_and_resume_does_not_rerun_workers` (303–329); S02 `ToolingSessionTests.test_candidate_drift_after_dispatch_is_retained_as_interrupted` (573–578) | Verify an interrupted durable prefix is retained, completed effects are not repeated and drift remains interrupted. S01 uses a real killed fixture process; S02 uses a synthetic adapter. Neither establishes native LLM recovery or historical intervention frequency. |
| C02 — coordination | S03 `GitAdapterTests.test_overlap_dependency_delete_binary_and_uncertainty_are_conservative` (79–97); S01 `RuntimeSchedulerTests.test_changed_footprints_limits_and_stale_inputs_never_start_workers` (191–204) | Check conflicting/ordered/unknown classifications and pre-dispatch refusal for changed effects, limits or source identity. Unknown coverage cannot become a safe admission. |
| C03 — coordination and recovery | S01 `RuntimeSchedulerTests.test_real_overlap_isolated_resources_and_serial_effect_agreement` (63–71), `test_dependencies_serialize_waves_and_reversed_order_is_safe` (73–81), and `test_new_recovery_grant_preserves_worker_journal_without_rerun` (270–285) | Check useful independent work, dependency serialization, private worker output agreement with the serial/effect oracle, and recovery without worker rerun. These remain fixed-patch controls; no native concurrency authority transfers. |
| C04 — continuity and handoff | S04 DDP-T08; S05 coordinator handoff | Construct a synthetic packaging task that retains source identity, actual dependency meanings, pending acceptance and rollback. The documents describe a delivery need; comprehension, intervention time and productivity benefit remain unobserved. |

S01's `setUpClass` (24–31) uses
S06 `GitRuntimeTests.setUp` (24–62), which creates the common `a.txt`/`b.txt`
base and patch inputs. C01 and C03 therefore share input ancestry when derived
from these fixtures. C02's S01 controls may share it too. Treat them as one
lineage wherever those inputs/answers/trajectories are retained; different family
names or filenames do not make them independent holdout units.

## Actual yield and exclusions at kickoff

| Population | Actual status at this registration |
|---|---|
| Proposed design families | Four: C01–C04. Family names are not observations. |
| New executable HAR cases | Zero created or independently qualified by this track. |
| Registered/evaluated HAR comparison units | Zero; no comparison roster or results were generated. |
| Native task sources | Zero collected or admitted; eligible yield is unknown until source/rights review. |
| Native sessions, human outcome ratings, observed user interventions | Zero obtained by this track; historical frequency and minutes remain unknown. |

Exclude credentials, private histories, unrelated repositories and hidden grader
material from candidate context. Preserve refused, malformed, missing and ineligible
source records in the authorized registration ledger rather than removing them
from the source-yield denominator. Existing source tests do not supply permission
for native collection or close `048/T008` or `049/T004`.

## Proposed cohort and leakage controls

For `049/T002`, propose a descriptive engineering cohort of **up to 16 case
definitions**, targeting four per family and an **8 discovery / 8 holdout** split
only if actual distinct lineage and both-axis coverage support it. No case IDs,
partition assignment, sample-size adequacy or eligible yield are claimed yet.
This proposal is not an inferential power calculation or a representative sample.

Before freezing a roster, record each case's source ancestry, immutable initial
state, patches/input artifacts, hidden oracle and answer provenance, interruption
points, expected effect domain, synthetic label, rights basis and exclusions.
Group all derivatives of a source/input/answer/trajectory lineage together. Add a
negative control in the future corpus validator that refuses the shared C01/C03
lineage appearing in both partitions. Shared generic runner/oracle implementation
is a separately declared provenance dependency; it does not by itself establish
independent task inputs. An unresolved lineage stays unassigned.

Keep grader files, answers, held-out labels and administrative registration
material outside the improver/solver's positive read inventory, even when the
repository stores them. Give the solver its visible task requirements separately.
Freeze the full label rubric independently of method rankings. Attempt every
holdout label, including failures/refusals; retain missing labels and actual
adjudication rather than inventing agreement. If disjoint lineages or either
axis's classes are insufficient, record that limitation and retain an incomplete
or inconclusive evaluation instead of silently changing the population.

Freeze static base A, simple guidance B and contrastive no-library C identities,
matched task/model/host/tool conditions and order. Experience arm D remains
conditional on `049/T006`, uses only earlier eligible entries and includes all
experience-generation costs. Multiple probes, retry attempts, interruption points
and comparator arms do not multiply the number of independent source cases.
Any reused base observation/cache needs an exact identity and pre-registered cost
allocation rule; no optimistic sharing is assumed here.

## Outcomes, costs and the next gate

Report continuity and coordination separately from the first executed case:

- Continuity: correct completion/recovery with registered and started denominators;
  repeated work, duplicate effects, checkpoint identity and actual interventions.
- Coordination: class-specific TP/FP/FN, precision/recall, false safe admissions,
  verified useful parallelism, unnecessary serialization and serial agreement.
- Shared: refused/failed/interrupted/ungraded units, label coverage, effect or
  authority violations, setup/context/proposal/probe/selection/verification/review/
  recovery/cleanup costs and observed versus unknown resource/quota/cash values.

A missing/zero denominator is undefined, not perfect performance. Fixture assertions
and synthetic cost literals are not measurements of native quality, human effort,
subscription consumption or economic utility. Mandatory review effort remains a
cost even when counted separately from corrective intervention.

Before evaluated outcomes, `049/T002` must freeze the actual eligible roster,
lineage groups/partitions, budgets, sample counts, task order, acceptance margins,
rubric, missingness/adjudication and stop rules. Independent outcome verification
(`049/T011`) and full cost reconciliation (`T012`) precede deterministic evaluation
`T003`, which also requires `048/T009`. Native collection remains a separate
conditional branch requiring qualified `048/T008`, `049/T004` and exact fresh
source/route/quota/operator authority. Automatic promotion remains disabled.

## Newer source checks that do not broaden admission

N01/N02, added with PR #655, preserve every supplied metadata attempt and classify
matching metadata as unknown (`full-verifier-not-run`); source admission and
execution authorization remain false. They can inform a source-registration
negative control, not certify a source population or permission. Original paths
must not be renamed or dropped to fit the finite patch domain.

N03's verifier-pin drift control and N04's shared command/byte-budget and native
prepare-cap controls are relevant engineering references. Their native wording
refers to existing local Git replay/preparation, not native Codex/Claude sessions.
No test was rerun or result imported by this inventory; current System One, FC.1,
telemetry and plugin acceptance remain independent.

## T001 re-registration at the current head (2026-10-27)

Status: inspection readback only. It supplements, and does not rebind, the
kickoff inventory above. Trace: SPEC-049/T001, REQ-001/SC-001, REQ-003/SC-003.

The anchors were re-read at repository head
`61b5c39cf6a499d7e7249af01df43b4f4f36981a` (`develop` after PR #775). Git blob
IDs and file SHA-256 values for S00–S06 and N01–N04 were recomputed from the
working-tree bytes and are byte-identical to the table above; the seven named test
methods still exist at the recorded line ranges (S01 63, 73, 191, 270, 303; S02 573;
S03 79). No inspected source drifted, so the kickoff identities remain the pinned
anchors. No test was rerun and no result is imported.

### Source-rights ledger (before any real collection)

| Source class | Members | Rights basis recorded | Status for collection |
|---|---|---|---|
| Repository tests and fixtures | S01–S03, S06, N01–N04 | `AGPL-3.0-only` SPDX notices in the files; owner-controlled repository | Admitted only as the basis for owned synthetic derivations; preserve notices and modification history. No outcome or behavior data. |
| Repository specification handoffs | S04, S05 | `CC-BY-SA-4.0` mapping via S00 and repository governance | Admitted only as the basis for an owned synthetic packaging task; they describe a need, not an observation. |
| Native repository tasks | none | No permission receipt exists | Not admitted. Requires per-source owner permission, privacy/secret inventory, reproducible initial state and an independent outcome definition (`049/T004`, `048/T008`). |
| Third-party benchmarks, datasets, provider transcripts, personal task material | none | None | Not admitted; no rights basis. |
| User intervention history | none | No record exists | Not available. Historical correction frequency and minutes are unknown and must not be reconstructed or estimated from these tests. |

This ledger is a registration of rights as read from repository notices and the
owner's stated authorization for this repository work. It is not an independent
ownership or license audit.

### Observed versus planned yield

| Quantity | Observed (inspected) | Planned (not yet obtained) |
|---|---|---|
| Direct case-source files | 5 (S01–S05) plus helper S06 | none added by this track |
| Named test-method anchors | 7 across S01, S02, S03 | additional anchors only if a future inventory finds them |
| Handoff documents | 2 (S04, S05) | none |
| Candidate lineage groups | 4 (L1, L2, L3, L4 in corpus.md); L3 may merge into L1 | disjoint lineages after construction; count unknown |
| Executable HAR case definitions | 0 | up to 16 proposed in this registration, not created |
| Registered/evaluated comparison units | 0 | not yet defined |
| Native sources, sessions, ratings, observed interventions | 0 | unknown until a permission review exists |

Observed counts are inspection counts of existing files. They are not independent
cases, trials or evidence of agent behavior. Planned figures are design targets only.
