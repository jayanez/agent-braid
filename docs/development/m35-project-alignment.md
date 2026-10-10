# M3.5 software delivery and project alignment — 2026-10-10

**Current boundary:** all six synthetic-software task issues are closed. Only the
real-workload experiment remains, through its four existing phase tasks; parent
#180 and milestone 9 stay open. Task IDs and empirical acceptance requirements
are preserved. The [compact experiment register](../../specs/019-native-predictor/software-completion.md)
is the current re-entry checklist.

## Delivered software and evidence

[PR #463](https://github.com/jayanez/agent-braid/pull/463), merged as
`c51c91ee270c84d6786355c20a49ee86cf38648e`, delivered the final deterministic
offline synthetic trainer/inference and verifier boundary. The evaluator and
adapter controls support software testing; the real feed is unavailable.
[115 focused controls](../experiments/evidence/m35-software-completion-2026-10-10/README.md)
passed without skips, including the three formerly skipped contracts, and the
package records independent Luna technical review and candidate-bound public
clone reproduction. This does not supply real labels, real trained-model
utility, human scientific approval or a founder experimental decision.

[PR #473](https://github.com/jayanez/agent-braid/pull/473), merged as
`526fa11c2a074abfe8c5c1217a4529a5f60ed4da`, repaired the global Spec Kit
public-provenance gate after the software squash. The earlier post-merge
[run 38040658427](https://github.com/jayanez/agent-braid/actions/runs/38040658427)
failed and remains a non-pass. The repair's
[exact-head CI](https://github.com/jayanez/agent-braid/actions/runs/38044420777)
and [post-merge CI](https://github.com/jayanez/agent-braid/actions/runs/38045064711)
passed: 885 tests, two explicit skips, and all four Codex/Claude integration
matrix configurations. The [repair package](evidence/spec-kit-public-draft-provenance-2026-10-10/README.md)
retains its 29 focused adversarial/regression controls and validation bindings.
The final merged repair was additionally checked in a fresh public clone.
These results describe those commits; this editorial alignment receives its
own validation and review through its pull request.

## Source, issue and private Project disposition

| Source tasks | Issue state | Private Project status | Scope |
| --- | --- | --- | --- |
| T002/#182, T004/#184 | Closed | Done | Synthetic trainer/inference and verifier boundary |
| T006/#186, T008/#187 | Closed | Done | Capture, sidecar, ledger, filtered export and seal tooling |
| T009/#222, T010/#223 | Closed | Done | Readiness checker and synthetic interfaces |
| T007/#188, T001/#181, T003/#183, T005/#185 | Open | Todo | Deferred experiment phases and source-bound adaptations |
| SPEC-019/#180 | Open | Review pending | Full experimental acceptance still absent |

The private [Project #6](https://github.com/users/jayanez/projects/6) was inspected
through the owner's existing authenticated browser session. All eleven linked
records and six completed subissues were present. The parent was corrected from
Todo to the configured Review pending; a reload confirmed persistence.
Repository token access remains insufficient for a Project API query, but the
UI verification resolves the previous unverified-board limitation without
expanding credential permissions. The Project README was updated to remove its
stale fixed inventory counts and pre-M2/M4 closure summary, link the current
source/index, and record the six software completions and four experimental phases.
Project statuses are planning metadata, not
source admission, reviewer approval or execution authority.

The milestone description and generated issue titles/task text follow the
merged source. Reconciliation is restricted to milestone 9, reviews the exact
operation digest, applies from clean develop, and ends with `operations: []`.
The final pull request records the executed digest and subsequent read-back;
this procedure does not close an unfulfilled experimental task.

## Documentation boundary

Current README, roadmap, architecture, technical-readiness, quickstart and
SPEC-019 planning/navigation now distinguish completed synthetic software from
the deferred experiment. Dated observations, authority/evidence snapshots,
original failed/interrupted runs and accepted ADRs retain their historical
bytes and claim boundaries; current entry points explain what supersedes them.
No unrelated milestone, runtime execution contract, source permission or
scientific threshold changes in this alignment.
