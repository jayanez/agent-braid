# M2 closure decision packet

**Prepared:** 2026-09-27

**Status:** in preparation; no M2 closure decision has been recorded.

**Starting revision:** `ecfaf24601154b0eaf4998e4d6c6a77b490cd093` (`develop`).

This packet keeps the bounded scientific assessment, clean-room reproduction,
radar disposition, founder decisions and GitHub tracking separate. The exact
candidate commit, reproduction output and review decisions must be filled from
the frozen SPEC-017 closure record; this starting revision is not that candidate.

## Claim and limit matrix

| M2 exit criterion | Evidence available before the final freeze | Limit to review |
| --- | --- | --- |
| Certificates reproduce from immutable fixtures. | [SPEC-012](../../specs/012-m2-git-replay-planner/spec.md) records fixed-patch exhaustive Git replay and independent evidence verification. [SPEC-013](../../specs/013-m2-real-workload/spec.md), [SPEC-014](../../specs/014-m2-observation-normalizer/spec.md) and [SPEC-015](../../specs/015-m2-counterexample-reducer/spec.md) add bounded internal reproductions. | Reproduction of the final combined candidate is pending. [SPEC-016](../../specs/016-m2-partial-order-reduction/spec.md) remains private; its verifier regenerates the oracle and uses the same replay implementation, not an independent engine. |
| The scheduler recovers parallelism over sequential execution. | SPEC-012's read-only preparation prototype and the accepted [SPEC-013 retest decision](../../specs/013-m2-real-workload/m2-retest-founder-review.json) record eligible parallel preparation and two 30-pair batches above the registered median threshold against serial preparation, with matching tracked trees and zero unsafe admissions. | Both schedulers formed the same single wave in that corpus. This does not establish a scheduling advantage, universal speedup or production performance. Recheck the registered inputs and hashes at the final candidate; rerun measurement if those inputs changed. |
| Observation is fixed before execution; raw traces retain excluded differences. | `tracked-tree-v1`, [ADR 0013](../adr/0013-isolated-git-replay-and-advisory-planning.md) and SPEC-014 define and exercise the bounded observation. | Complete fixed-patch replay only; terminal projection is not contextual equivalence, and incomplete runs remain distinct. |
| Destructive and external effects default to safe policies. | The reviewed local prototype prepares in read-only isolated workspaces; planning artifacts retain `executionAuthorization: false`. | There is no authorization for arbitrary tools, live agents, ref promotion, executable integration or external effects. |

The [readiness review](M2_READINESS_REVIEW.md) gives the detailed assessment.
This matrix is a review guide, not new experimental evidence.

## Required gates, in order

1. Complete and obtain explicit founder approval of the bounded M2
   [milestone-radar review](../../research/radar/README.md). Radar review does
   not adopt a signal or change an implementation contract.
2. Integrate the SPEC-017 protocol and all closure inputs. Pass Spec Kit and
   the quick and PR validation profiles, then freeze one exact candidate.
3. Reproduce the candidate in a fresh clone and isolated Python 3.12+ environment
   with pinned dependencies and complete reviewed history. Capture commands,
   versions, input hashes, exit codes, raw outputs, negative controls and clean
   initial and final repository state. A changed candidate invalidates the run.
4. Obtain a founder **scientific review** of the evidence and limits against
   that exact candidate, with conflict of interest and
   `independent_validation: pending` stated explicitly.
5. Obtain a separate founder **M2 milestone-closure decision** against the same
   candidate and reproduction. A scientific review alone does not close M2.
6. Only if closure is approved, publish the bounded closure record, change the
   GitHub tracking source for SPEC-012 through SPEC-017 and M2, run guarded
   reconciliation, and verify the resulting Issues, milestone and Project.

The founder may approve, request changes or reject each decision separately.
No unchecked or absent gate is inferred from a successful validator or a closed
task issue. External independent validation can remain pending under
[Governance](../../GOVERNANCE.md); it cannot be claimed as complete.

## Founder decision prompts

These prompts are proposed review questions, not decisions or signatures:

1. **Scientific review:** Does the exact candidate's clean-room record support
   the four M2 exit criteria only within the fixed-patch Git domain and the
   limits above, including SPEC-016's private scope? Record the candidate SHA,
   evidence IDs, reviewer, conflicts, decision and any required corrections.
2. **Milestone closure:** Given the approved scientific review and radar review,
   should M2 close internally against that same candidate while independent
   external validation remains pending? Record a separate yes/no/changes-needed
   decision and the permitted public claims.

Neither question authorizes execution, release publication, repository
visibility changes, public contract expansion or ref promotion.

## Tracking snapshot and reconciliation boundary

At preparation time, GitHub milestone M2 (#4) was open with five open parent
issues for SPEC-012 through SPEC-016 and 30 closed task issues. The
[tracking source](../development/github-tracking.json) likewise keeps M2 and
those parents open. SPEC-017 will be registered open after its stable IDs are
integrated. Parent and milestone closure belongs after the separate founder
decision. The five M2 parents were inspected in the private Project's **Specs
and tasks** view and set to **Review pending** on 2026-09-27. Their task progress
remained 13/13, 6/6, 3/3, 3/3 and 5/5 respectively. The available CLI token
lacks `read:project`, so this Project status is a UI observation, not a result
of the repository Issues audit. Recheck membership and status after SPEC-017
is added and again after any closure decision.
