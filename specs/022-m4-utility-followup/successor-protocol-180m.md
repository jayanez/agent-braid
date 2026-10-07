# Prospective 180-minute successor

The owner approved implementation and evaluation preparation of option 1 on
2026-10-07. The actual statement, reviewed proposal SHA-256 and durable ref are
in `successor-protocol-review-20261007.json`. The frozen feasibility proposal is
preserved byte-exact; its pending status describes that historical proposal,
not the subsequent recorded decision. This is a scoped protocol disposition,
not whole-feature assurance or registered capture approval.

## Version identity and compatibility

The existing `spec022-paired-evaluation-plan-v1` remains the default with exactly
45 minutes. Preparation explicitly selected with `--plan-version v2` produces
`spec022-paired-evaluation-plan-v2` with exactly 180 minutes. Unknown versions,
unknown horizons and cross-version horizon combinations are refused. The library
builder takes the full `plan_version` identity; the CLI maps `v1` and `v2` to
those identities. No arbitrary horizon flag is introduced.

Keep all nine corpus rows, five pinned numeric exclusions, 22 paired slots per
admitted block (two warm-ups and twenty measured), parity order, unique fresh
private destinations, source identity, admission proofs, caps, grants, independent
verification, phase/residual accounting, refusal and recovery rules. The
successor changes only the outer no-new-dispatch horizon. It selects no runtime
optimization and introduces no paid/model/provider/host calls.

## Review and incomplete outcomes

Separate capture review must match exact manifest SHA-256 and public candidate.
For v2 it must additionally identify
`reviewedPlanVersion: "spec022-paired-evaluation-plan-v2"`. An explicitly supplied
version must match v1 too; absent version remains compatible with legacy v1
records. Neither legacy approval nor this implementation/preparation decision
can be replayed as v2 capture authorization. The preparation CLI continues to
refuse execution flags.

Both pre-dispatch and post-treatment deadline checks use the validated version's
horizon. Active bounded work may finish normally after expiry; retain its raw
observation, mark the whole protocol incomplete and preserve all remaining slots
as unexecuted. Even expiry during the final treatment cannot produce a positive
complete-protocol outcome. Safety/identity stops retain their stronger disposition.

## Candidate-bound preparation and later gates

Changed preparation/trial code inputs require fresh matching exploratory diagnostic
records on a clean candidate. Historical diagnostic/manifest bytes remain evidence
of their own inputs; do not relabel them. Prepare a new immutable v2 manifest only
after exact diagnostic/admission checks. Plan generation creates no fixture copies,
grants, runtime treatments or registered measurements.

Review the stable public harness, exact new manifest and separately enumerated
fresh-process controls before requesting capture authorization. Registered
synthetic results remain descriptive; actual-workload source rights/protocol,
capability dispositions, clean-room reproduction, independent whole-M4 review and
a new founder decision remain separate. T005/T006 and M4 stay open.
