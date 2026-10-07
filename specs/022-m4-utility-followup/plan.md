# Implementation plan

## Technical context and scope

Use the standard-library runtime and the existing `scripts/measure_m4_alpha.py` implementation as the starting point after verifying its actual entrypoint. Add a separate `scripts/measure_m4_utility.py` follow-up harness and phase counters at existing coordinator boundaries. No core dependencies or runtime contract changes. Keep SPEC-021 measurements immutable.

## Constitution check before research

Articles 6/12 require point-of-use correctness and isolation; 13/14 require inspectable uncertainty; 19 requires useful workloads and costs; 20 keeps analysis authority separate. Mandatory checks cannot be cached away, sampled away or omitted to manufacture speedup.

## Research, assumptions and alternatives

Compare serial and the current admitted parallel mode first. Use phase measurements to choose at most one cost improvement before the registered evaluation, documenting its code delta and expected effect. If no contract-preserving improvement is justified, evaluate the unchanged implementation and report that result. Retain serial policy as the operational fallback. Adaptive admission is a later contract, not an inferred consequence of this experiment.

## Design and compatibility

Use the exact ordered inventory and identities in `technical-review-packet.md`, `workload-manifest-candidate.json` and `evidence/prepared-fixture-manifest.json`. These are draft synthetic preparations, not admitted runtime evidence. Prepare private owned deterministic fixtures: 2 and 4 independent operations, each editing a distinct file; and a 4-operation dependency chain. Cross these with inserted payload sizes 1 KiB, 64 KiB and 1 MiB per operation, provided existing aggregate request/output/scratch caps admit the complete fixture. A refused size is a reported exclusion, never a reason to widen budgets. Immutable identities have been generated once per block. Preserve all nine cells, including five direct patch-cap exclusions; the four numerically remaining blocks require admission checks. The dependency chain declares order between distinct-file patches against a common base, not cumulative source ancestry.

Freeze the manifest and instrumentation on a clean candidate before timing. For each admitted block run 2 unmeasured warm-up pairs followed by 20 measured pairs. Alternate serial-first and parallel-first by repetition parity. Use fresh run/grant directories for each treatment, identical fixture and a fixed ordered workload manifest. Do not claim controlled OS cold caches. Record hardware, platform, Git/Python versions, background-load observations and all errors. No replacement trials or deletion of outliers.

Primary outcome is median paired serial/parallel full-wall ratio per independent block. The descriptive usefulness target is >=1.10 with zero unsafe admissions and equivalent verified trees for every admitted run. Chain controls must preserve dependency order and serial outcomes; they are not pooled into the independent-workload utility metric. Report each block, invalid pairs and first/subsequent exposures. An invalid treatment leaves its pair visible and makes the block's utility decision inconclusive; do not compute a favourable complete-case acceptance. These 20 local pairs are descriptive engineering observations, not a population or causal speedup claim. This repeated-character synthetic corpus supports synthetic diagnostics only. A ratio >=1.10 cannot itself close Article 19 actual-workload evidence, practical utility, G4 or M4 acceptance; actual workload/source-rights evidence and a separate founder decision remain necessary.

Record per-phase wall and CPU, command count, bytes and actual overlapping intervals where the existing process runner exposes them; mark unavailable values explicitly. Include timing instrumentation overhead within the operational treatment interval. Follow the exact packet's disjoint phases and residual accounting. Report final observer sealing/output and shared artifact writing separately outside that interval; never claim them as included or free work. The proposed 45-minute budget stops new registered dispatch, not processes by hard kill. Retain existing scratch/RSS measurement limitations. Never add artificial sleeps or unrelated workload work to obtain a speedup.

## Validation strategy

Map SC-001..004 to `quickstart.md` and planned `tests/test_m4_utility.py`. Replay forged grants/evidence, stale inputs, unknown footprints, missing traces, interruption and duplicate delivery controls using the current runtime tests. Run quick after coherent implementation and PR once stable. Fresh process reproduction and measurement are separate commands bound to the clean candidate.

## Constitution check after design

No execution capability is added. The observation remains tracked trees and explicit runtime effects. Any proposal to skip consumer verification, weaken refusal or change authorization is rejected from this feature.

## Human review and unresolved decisions

The exact `technical-review-packet.md` supersedes prior vague corpus/phase descriptions. The owner approved its frozen public candidate `3777e578` on 2026-10-07; `protocol-review-3777e578.json` records the scoped decision and T001 is complete. Instrumentation and evaluation preparation are authorized; whole-feature assurance remains draft/human-review pending. Registered measurements require a separately reviewed stable harness/manifest freeze. Founder utility decision follows obtained results; NO-GO and M4-open status remain unchanged before that decision. No scientific or independent validation is implied.

## Prospective 180-minute successor

On 2026-10-07 the owner selected option 1 of the byte-frozen `capture-feasibility-packet.md`: implementation and preparation of a distinct 180-minute version only. `successor-protocol-review-20261007.json` records the actual statement and proposal identity. Preserve v1 at 45 minutes, all corpus/sample/resource/grant/verifier rules and the negative/incomplete outcomes. `successor-protocol-180m.md` describes explicit version selection and future exact review; new preparation/trial inputs require fresh candidate-bound diagnostics. This scoped decision does not complete T005 or T006 and grants no registered dispatch or whole-M4 acceptance.
