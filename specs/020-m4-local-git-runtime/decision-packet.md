# First M4 increment: acceptance packet

The bounded local Git runtime is implemented, independently reviewed and locally
validated. SPEC-020 technical tasks T001–T007 are complete. Founder acceptance
remains pending; ADR 0019 is Proposed, and M4 remains open.

## Candidate and scope

The executable candidate is `7abe73ee27f0d469b78a1a01320ab5acd9d5aa0a`, based on
public develop `7a1a3b080141f5936d6c694d83043a1580923838`. The final frozen
assurance record binds the packaging commit containing the same executable
inputs and their evidence. Approval must identify that frozen commit.

The increment admits 2–4 immutable ordinary-text Git patches, explicit effects
and serial dependency order, digest-bound authorization, a new private Git
result, verified checkpoints, interruption recovery and abort. Existing analyzer
contracts and the frozen M2 process runner remain unchanged. No source refs are
promoted. Public API additions and versioning are described in
[the specification](spec.md) and [quickstart](quickstart.md); records are
`0.1.0-alpha` and opt-in.

## Obtained validation

- Final PR profile: exit 0; 326 tests in 749.856 seconds, 4 explicitly skipped.
  The skips are three deferred SPEC-019 tests and one unavailable private
  historical-object control. All selected repository, contract, publication,
  radar, adoption, CLI, finite scientific-control, Spec Kit and whitespace
  checks passed. [Raw profile log](../../examples/runtime/m4-local-git-pr-validation.txt).
- Separate independent-object-store clone: 15 runtime tests passed in
  211.480 seconds on Darwin arm64, Python 3.13.11, Apple Git 2.54.0.
  Clean working tree; no input changes during the run. Git fsck and Spec Kit
  preflight also passed. [Hashed reproduction](../../examples/runtime/m4-local-git-reproduction.json)
  and [raw output](../../examples/runtime/m4-local-git-reproduction.txt).
- Luna Latest independent design and implementation review: two reproducible
  findings corrected and independently verified. Final runner separation and
  four focused boundary tests passed; no reproducible findings remain in the
  reviewed scope. [Review record](implementation-review.json).
- Earlier quick profile failed on the initial candidate: ELOOP translation,
  stale inventory expectations and modification of M2 hash-bound runner bytes.
  All were corrected; the shared runner was restored byte for byte. An earlier
  PR run was interrupted for that correction and is not counted as passing.
  The final complete profile above supersedes those attempts without changing
  historical approvals or hashes.

## Observation limits and pending decisions

This is bounded software evidence on owned local fixtures, not evidence of
semantic code correctness, production readiness, independent scientific
validation or whole-M4 closure. Linux directory publication is implemented but
not reproduced on a Linux host. There is no hard child-memory cap. Same-UID
hostile interference, power loss, external effects and arbitrary commands are
excluded. Time, command, output and sampled scratch limits are enforced within
the stated contract. M3/M3.5 real verification scenarios remain separately
blocked and were not required or claimed by this increment.

The proposed founder decision is to accept the first SPEC-020 cut and adopt
ADR 0019 against the frozen candidate. Human review remains `pending` until an
explicit decision is permanently recorded. No external publication, remote
tracking synchronization, pull request or merge has been performed by this
local delivery. Any public integration requires its reviewed PR and versioning
record under GOVERNANCE.md.
