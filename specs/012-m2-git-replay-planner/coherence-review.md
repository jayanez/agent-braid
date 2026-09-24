# SPEC-012 cross-artifact coherence review

**Review date:** 2026-09-24
**Base:** `origin/develop` at `fd7c2d939cbcc8aaeb47e625e5c8a93d4b5f2bc8`
**Decision boundary:** Editorial and traceability review only. This record does
not approve a new experiment, close M2, establish independent validation, or
authorize result promotion or concurrent integration.

## Findings and disposition

| ID | Severity | Location | Authority and finding | Disposition |
| --- | --- | --- | --- | --- |
| C012-01 | Medium | `spec.md`, REQ-001; `plan.md`, validation strategy; `tasks.md`, T001/T002/T007/T008 | The historical `assurance.json` already records SC-009 and its path/patch-bound test, but the spec and task trace omitted that stable ID. The requirement stated the bounds, yet the scenario inventory was incomplete. | Add SC-009 with the existing 64-path/1-MiB boundary and test outcome; align the plan and task references. Do not rewrite the frozen assurance or evidence. |
| C012-02 | Medium | `tasks.md`, post-cut introduction; `plan.md`, follow-up heading and introduction | T009–T013 were checked and reviewed within their stated scopes, while introductory text called them unfinished. The T012 and T013 review records, ADR 0014, and the later plan paragraphs establish the scoped state. | State that these tasks are complete within their recorded scopes and name the remaining M2 risks separately. Keep the milestone open. |
| C012-03 | Informational | `m2-followup-evidence.json`, candidate status and limits; `t013-review.json`, decision | The evidence packet retains pre-review wording such as “T013 review pending.” It is a captured historical packet; the later review record contains the scoped founder acceptance. | Preserve the packet bytes and read the later decision separately. Independent validation remains pending. |
| C012-04 | Pending external reconciliation | `docs/development/github-tracking.json`, SPEC-012; GitHub tracking audit | The repository maps SPEC-012 to open M2, with all 13 tasks checked, but its GitHub parent/subissues have not yet been created. | After this correction PR is reviewed and merged, audit the merged source, apply only its reviewed operations, and audit again. Verify private Project views separately. |

## Traceability and limits

REQ-001–005 and SC-001–009 each have a scenario in the historical assurance
record. Every scenario names an existing test method and obtained evidence.
SC-009 uses `GitReplayTests.test_enforces_changed_path_and_aggregate_patch_bounds`.
The original first-cut approval remains bound to `7541ff4`; the T012 decision
and T013 R1–R6 acceptance retain their own reviewed hashes and scopes. None of
these historical decisions approve the current documentation edit by
implication.

The fixed-patch `tracked-tree-v1` observation does not establish semantic
correctness or safe live-agent interleavings. T013 prepares patches concurrently
but integrates the candidate tree serially and read-only. Resource sampling
overshoot, uncatchable coordinator crashes, project validation, concurrent tree
merging, and independent validation remain outside the accepted scope.

## Verification boundary

Spec Kit structure, GitHub tracking source, paired replay tests, and the
repository quick/PR profiles must be run on the proposed correction. The
repository's shared Git object store contains unreachable objects, so Spec Kit
validation must also be reproduced in a clean clone with the historical M2
source branch reachable. Passing checks do not replace PR review or founder
authorization to merge.
