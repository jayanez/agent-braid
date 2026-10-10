# Public Spec Kit draft-history repair — 2026-10-10

Squashing [software PR #463](https://github.com/jayanez/agent-braid/pull/463)
left SPEC-019's historical snapshots outside `develop` ancestry. The post-merge
[validation run](https://github.com/jayanez/agent-braid/actions/runs/38040658427)
failed the portable binding for ADR 0017. The exact already-public candidate is
retained by its annotated tag; this repair validates its unchanged draft/pending
record against that candidate and then runs ordinary strict historical checks.

Code candidate: `76aaca58da1aa6678cf07c648fe4bac264e506a7`. [receipt.json](receipt.json) commits all executable
inputs and raw log hashes. Gzip files preserve the successful raw bytes.
Superseded interrupted profiles (exit 130) are not passes; their hashes and
dispositions are recorded, with raw local-path diagnostics retained outside Git.
Two final independent
Luna Latest reviews at medium effort found no material issue in this bounded
repair. They do not supply human scientific or founder approval.

Executed: 29 focused history controls; quick (escalated to sensitive) and stable
PR profiles, each executing 885 tests; clean public
clone restoration, the complete Spec Kit gate and empty unreachable-object fsck.
The PR profile ran in a separate clone with its own isolated Python environment.
The quick profile also executed the pinned solo/dual integration matrix.
Exact-head hosted CI and post-merge verification must still be checked at delivery.

The adversarial review led to fixes and regressions for canonical Git ancestry
(replacement objects and legacy grafts ignored), wrong/additional public roots,
atomic restoration and exact advertised identities, counterfeit local approvals,
recreated annotated tags, and changed published assurance/review bytes. Changed
retained approval metadata fails before ancestry selection or fallback. All six
published reviewed-metadata commitments were independently recomputed from merged
`develop` commit `c51c91ee270c84d6786355c20a49ee86cf38648e`.

No assurance, human review, immutable export manifest, Constitution, experiment
threshold or feature contract is rewritten. T002/T004 software acceptance and the
[compact pending experiment](../../../../specs/019-native-predictor/software-completion.md)
remain distinct. No source capture, annotation, real fitting, experiment result,
model promotion or milestone closure is established by these structural checks.
