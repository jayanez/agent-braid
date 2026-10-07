# Registered capture feasibility and successor proposal

Status: owner decision pending. No approval, registered measurement or utility acceptance is recorded here.

## Current approved candidate

The existing protocol at public `3777e578ba3f8130d6f284acf54898198a45e0f0` remains byte-exact: nine blocks, five fixed numerical exclusions, two warmup plus twenty measured pairs for each of four eligible blocks, alternating treatment order and a **45-minute registered dispatch budget**. Source patch, execution, grant and verification budgets remain unchanged.

Preparation on clean public `5cb144e1193a266645e012a7f31224d846ea7003` produced a reviewable 176-treatment manifest with SHA-256 `6b7f7ed31e5599e4c17c313f9acb1225a95bce8eda17e4bc5598c36806031af5`. It created no fixture copies, grants or runtime treatments. A subsequent independent Luna review found a final-treatment deadline edge; its fix changes a bound input. Therefore this prepared manifest is a superseded preparation checkpoint and **must not authorize dispatch of the corrected candidate**. Prepare and review a new candidate-bound manifest after the correction is stable and public.

## Feasibility observation

The four exploratory pair walls total 303.193787792 seconds. Multiplying by 22 pairs gives a rough **111.1710555-minute** dispatch projection. This is a linear planning estimate from one serial-first pair per block under uncontrolled load and caches. It is neither a registered duration nor a guarantee. Preparation and final observer writing are separately observed outside operational treatment intervals; no cost is described as free.

An unchanged 45-minute run remains an available bounded experiment if specifically approved, but it may stop incomplete. Exhaustion must remain incomplete even if it occurs during the final treatment; active work finishes normally, its raw observation is retained, and no positive complete-protocol result is reported.

## Proposed separate prospective dispatch version

The recommended next decision is a **new prospective protocol version**, before any registered outcome is seen, with a **180-minute dispatch horizon**. This rounds the observed 111.17-minute projection plus approximately 50% planning headroom (166.76 minutes) upward. It increases only the outer dispatch horizon; it does not weaken per-stage completion/cancellation, patch/path/resource caps, grants, source identity, independent verification or refusal rules. The chosen numeric horizon is a proposal, not an approved budget or guaranteed completion time.

Keep the same nine-cell corpus, five exclusions, 22 pairs per admitted block, parity order, raw denominators, no replacement trials, no pooling chains with independent workloads, full phase/residual accounting and 1.10 **descriptive synthetic** ratio. No runtime optimization is selected. No prior pair is relabeled registered. No paid/model/provider/host calls are introduced. A safe negative result remains legitimate.

Implementation must retain the existing v1 manifest and runner behavior at 45 minutes. A successor manifest needs a distinct version, exact 180-minute field and an explicit matching review bound to its full public candidate and manifest hash; a v1 approval cannot authorize a v2 run. Pure tests must reject unknown versions/horizons, cross-version approval replay, missing rights/identity, reordered or omitted rows and unsafe outcomes. Registered capture and its separately enumerated fresh-process controls still require the later exact stable-harness/manifest approval. Any changed preparation/trial code input requires fresh matching exploratory admission records before preparation; legacy hashes are not refreshed to conceal drift.

## Owner decision requested after freezing this proposal

Choose one scoped disposition:

1. Approve this prospective **180-minute successor protocol for implementation and evaluation preparation only**. This does not authorize registered dispatch, actual-workload utility, G4 or M4 acceptance. A new stable candidate/manifest packet follows.
2. Keep the original **45-minute protocol** and review a corrected stable candidate/manifest for bounded capture, explicitly accepting that an incomplete protocol may result. This decision alone is not the capture approval.
3. Request a different justified prospective horizon or changes before implementation/preparation.

Do not mutate the previously approved protocol or manufacture an approval record from this document. Record the actual owner statement, reviewed proposal bytes and clean candidate only after the owner responds. The registered synthetic strand remains separate from the permissioned real-workload evidence and later whole-M4 decision.
