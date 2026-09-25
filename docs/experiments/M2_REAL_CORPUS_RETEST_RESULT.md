# M2 real-corpus performance retest

**Status:** Completed finite experiment; internal result review and external
human validation pending. This result does not close M2 or promote a ref.

The founder accepted the exact [PR #141 proposal](M2_REAL_CORPUS_RETEST_PROPOSAL.md)
at `87640e950d0ac3231a93446225ef7608ebe3d980`; the
[decision record](../../specs/013-m2-real-workload/m2-retest-founder-decision.json)
binds its bytes. The [full raw result](evidence/m2-real-corpus-performance-retest.json)
was captured from the checker/runner branch at
`98e68d01e31e8addee6afc5b8813963ac96b0292` in the pinned offline Linux
ARM64 image. Its SHA-256 is
`0b3b5c3496bcc9de9d6c324d3ca2765fbad19868755f89e5a8f5253a4f0e962f`.
After capture, commit `e77ef61ae7bf6611048c2b0ca9cf55cedec97929`
strengthened rejection-path output location checks. It did not change the
candidate implementation or the measured runner at the recorded commit; no
new experiment is claimed for that later commit.

## Paired Git preparation

Each independent batch contains 30 paired samples. The statistic is the median
of paired fractional improvements; intervals are seeded 10,000-resample
bootstrap 95% intervals. Both comparisons passed the registered requirement:
median at least 10% and interval lower bound above zero in **each** batch.

| Batch | Versus equally optimized serial | Versus timed path-overlap baseline |
| --- | ---: | ---: |
| 1 | 11.33% (9.79–14.11%) | 40.82% (39.32–43.47%) |
| 2 | 12.62% (11.85–14.23%) | 40.65% (39.25–43.79%) |

Candidate patch-preparation phase medians were 33.77 and 33.29 ms, versus
48.77 and 48.98 ms for serial. Candidate integration phase medians were 50.80
and 49.82 ms, versus 115.21 and 111.52 ms for the frozen path baseline. Both
schedulers formed the same single wave on this corpus, so the path-baseline gain
measures implementation overhead rather than a scheduling advantage. Median Git
command counts were 10 for candidate and serial, and 13 for the path baseline.

## Tree, source and command checks

All 60 pairs completed with matching candidate, serial and path-baseline tracked
trees: `fbc0d05bb42d2d94bb237d7f0b846457d0bd5940`. Source fingerprints
remained unchanged and unsafe admissions were zero in every pair. The seven
host-side remote-ref snapshots matched the pinned base, workstream, candidate
and proposal heads. Two private materialization pairs produced the same tree.
The four isolated candidate/serial test lanes each passed 204 tests using only
`python -m unittest discover -s tests`; none truncated output or changed its
tracked tree. No repository ref was promoted.

## Earlier incomplete attempt

The first run produced one valid 30-pair batch, but the host runner treated the
internal `measurement-complete` status as a failing process exit and stopped
before its post-batch ref check. It is **not** one of the two accepted batches
above. The [raw first batch](evidence/m2-real-corpus-performance-attempt-1-batch.json)
has SHA-256
`a444c7501550132afa90824d0f054e25c557acb08d8bbfc5deda00a404e1c3f3`;
the [failed host result](evidence/m2-real-corpus-performance-attempt-1-result.json)
has SHA-256
`a18cb9458482a2d40344ccc6e1c58e93596f3c7e8be5997601b178108e184e00`.
The exit interpretation was corrected and tested before the complete retest.
The earlier negative T003 result also remains unchanged.

## Boundary

This is empirical evidence for two registered Agent Braid workstream commits on
one pinned machine/image and one tracked-tree observation contract. Static
declared footprints and passing unit tests cannot establish all runtime effects,
general confluence, live-agent safety or a universal speedup. Review of the
new result is internal until separately accepted; independent external
validation and M2 closure remain pending.
