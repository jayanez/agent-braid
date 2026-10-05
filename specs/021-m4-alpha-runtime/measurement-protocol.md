# Frozen bounded M4 measurement protocol

Freeze this document and the measurement script in a clean candidate before any
measurement run. Implementation unit tests are separate from these trials.

## Corpus and controls

Owned deterministic Git fixtures: independent ordinary-text edits to two existing
files; four independent edits (two existing files and two new files); a dependency
chain of two edits. Full commit IDs, patch digests, input/final tree IDs and source
hashes are captured by the script. The primary comparison uses the two-independent
case in both admitted orders. Four-worker and dependency cases are coverage probes,
not additional samples in the primary comparison.

Run three paired repetitions per order. Alternate serial-first and parallel-first
according to repetition parity. Every treatment gets a fresh run destination and
grant store and freshly rehearsed policy plan. Reuse the same immutable fixture;
never flush system caches. Report repetition one and later repetitions separately
as first/subsequent exposures, without claiming controlled cold/warm OS caches.
No model calls, external repository corpus, source promotion or arbitrary commands.

## Outcomes and cost boundary

Require equivalent independently verified final trees and zero unsafe admissions.
Capture actual worker intervals, recorded writable scopes, conflicts refused,
forgery/unknown footprint rejection, missing/corrupt trace rejection, cancellation,
fresh-process kill/resume/abort and duplicate delivery diagnostics in the associated
frozen reproduction suite. An unexecuted control remains explicitly pending.

Wall time begins before evidence/advisory production and ends after consumer
verification and treatment cleanup. Capture parent CPU, aggregate child CPU,
Git command count and captured output from all bounded phase budgets, sampled peak
scratch, and process-lifetime peak child RSS. Do not call the RSS a per-run peak or
sum phase scratch peaks as simultaneous storage. Instrumentation overhead and
uncontrolled OS cache/background activity are disclosed. Grant issuance and all
verification/rehearsal costs are included; worker-only timing is secondary.

For each pair report serial and parallel total wall nanoseconds, serial/parallel
ratio and deterministic outcome. Report raw samples and median ratio; three pairs
per order are descriptive and do not justify population confidence or causality.
Positive speedup is not required. Negative/inconclusive usefulness needs a separate
founder go/no-go at G4. Protocol adherence is assessed independently of direction.

## Binding and reporting

Record candidate SHA, clean-state/source inventory before and after, platform,
Python/Git/host versions where relevant, protocol/script hash and raw output hashes.
Changing code or protocol invalidates the bound run. Fresh Darwin and Linux
reproductions and independent Luna review are separate records. Neither these
measurements nor passing tests authorize milestone closure, publication, paid
model consumption, scientific claims or founder acceptance.
