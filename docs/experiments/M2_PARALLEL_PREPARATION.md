# M2 parallel Git preparation performance follow-up

The founder accepted SPEC-013 T006 at commit
`60d6bcaba7245e9864298321b1038cddfde6fd9e` as a bounded, internally
reviewed **negative performance result**. Its two completed real-corpus runs
were slower than serial. This follow-up does not replace or revise that record.

## Goal and method

The priority M2 goal is a reproducible median reduction of at least 10% in
measured Git lane time against both an equally optimized serial lane and a
timed path-overlap baseline. Lane time includes patch preparation, fixture
commit materialization and tree integration; common analysis and worktree
setup are outside that metric. A seeded, paired bootstrap 95% interval must
also exclude zero improvement for each comparison. Tree identity, source
immutability, fail-closed classifications and resource limits remain gates.

`scripts/benchmark_m2_parallel_preparation.py` creates deterministic small
two- and three-operation fixtures and a separate two-operation shape proxy.
The proxy has three and five disjoint tracked paths and 7,608 and 56,636
patch bytes. These are within 5% of the reviewed T003 workstreams' 7,872 and
55,208 patch bytes; the proxy contains generated text, not their source code.
It does not reproduce their add/modify mix, Git history or patch hunks.
Each run contains 30 paired samples, alternates candidate versus serial lane
order, and alternates current versus baseline process order. The shape proxy
was run twice with identical code and script bytes. Every sample checks all
four final trees, the source repository, completed status and unsafe
admissions.

The path baseline uses the byte-verified T003 prototype module at `60d6bca`
with a conservative tracked-write overlap scheduler. Its imported Git process
helper retains the 10 ms default poll. The current prototype uses a 1 ms poll
for **both** candidate and serial lanes. This checks cancellation and process
completion more often; it does not relax the 50 ms scratch sampling, hard
child address-space limit, command/output budgets or wall deadline. The
prototype also avoids a redundant first merge and final tree lookup in both
lanes. The benchmark executes Git-only synthetic fixtures; it runs no project
test command or live agents.

## Observed result

| Fixture, 30 pairs each | Candidate median | Serial median | Path median | Paired gain vs serial | Paired gain vs path |
| --- | ---: | ---: | ---: | ---: | ---: |
| Small, 2 operations | 101.14 ms | 117.77 ms | 165.47 ms | 13.72% (95%: 11.92% to 14.69%) | 33.97% (95%: 32.64% to 42.09%) |
| Small, 3 operations | 173.73 ms | 193.59 ms | 250.27 ms | 9.997% (95%: 7.86% to 11.68%) | 30.32% (95%: 26.05% to 33.01%) |
| Shape proxy, run A | 105.34 ms | 118.59 ms | 162.89 ms | 11.11% (95%: 9.58% to 13.02%) | 36.59% (95%: 31.39% to 40.75%) |
| Shape proxy, run B | 104.05 ms | 118.94 ms | 166.00 ms | 13.64% (95%: 11.60% to 15.71%) | 37.39% (95%: 35.00% to 41.00%) |

These percentages are medians of **paired fractional improvements**, rather
than ratios of the displayed lane medians. Pooling the two shape-proxy runs
gives 12.54% against serial (95%: 10.82% to 13.67%) and 36.82% against path
overlap (95%: 34.78% to 40.10%); the independent run summaries above remain
the primary reproducibility check. The three-operation small fixture remains
just below 10%, and no changed-code real-corpus result exists. **The M2 goal
is therefore still open.** Both schedulers form the same single wave on these
disjoint-path fixtures, so the path-baseline gain is implementation cost
reduction, not a scheduling advantage. All measured lanes produced the same
final tree, left their sources unchanged and reported zero unsafe admissions.

The [small-fixture report](evidence/m2-parallel-preparation-synthetic-30.json)
and shape-proxy [run A](evidence/m2-parallel-preparation-shape-30-a.json) and
[run B](evidence/m2-parallel-preparation-shape-30-b.json) retain all phase
timings. These are median paired candidate-minus-serial differences in
milliseconds; negative values favor the candidate:

| Fixture | Patch preparation | Commit materialization | Tree integration |
| --- | ---: | ---: | ---: |
| Small, 2 operations | -15.62 | +0.38 | +0.18 |
| Small, 3 operations | -19.59 | +0.68 | -0.97 |
| Shape proxy, run A | -13.81 | +0.69 | +0.11 |
| Shape proxy, run B | -16.22 | +0.07 | -0.40 |

Candidate and serial issue the same 10 Git commands for two operations and 16
for three. Their measured difference comes from concurrent patch preparation;
commit materialization and tree integration remain mostly serial. The frozen
path baseline issues three more commands in two-operation integration and
uses the 10 ms poll. Phase medians are descriptive and need not add up to the
median total.

All reports were produced with Linux ARM64 image
`sha256:edddb1cbcbccb0e1af6505f9ff9938905da6f79303c97d1d12092ef61508f005`,
Python 3.12.13 and Git 2.47.3, offline with two CPUs, 2 GiB memory and 512
processes. Report SHA-256 values are `cce66046f5bf47d9807a19e409e61fc9be9a5f83a9b5f563210aa3fe61bf98fd`
(small), `70981f175ab08439521b893a583a970836e81a8b86ec21953af7872dcff73a9c`
(shape A) and `9005e41aa6bb4b4f648ad178907bda9fd41354fbf4063580b7f757710afc9f26`
(shape B).
The script verifies frozen module SHA-256
`3daf9c4ae946ab9a59fb4c2711492468ffdb6455a0bf04f6318a99b7664db860`.
The measured candidate prototype SHA-256 is
`8e77bf6a27993be13188249bab64c1ec331c120438dc170cc47e323fb3854c4e`;
the Git process helper SHA-256 is
`3247ac861404cfb68f08939770a5048294b45ddc984a1379ca9eb2091ad48668`;
the benchmark script SHA-256 is
`c277952b9b17ba93db5970716f30dff45bf7cad0c66b9df27b5b13583f381111`.
Reproduction runs that script with `--samples 30`, `--shape-proxy` for the
two-workstream proxy, the byte-verified T003 module passed as
`--frozen-module`, and an explicit `--output` path under the same pinned,
offline container limits.

## Next decision

The optimized runner has **not** executed a new ADR 0015 real-workload
experiment. A real-corpus comparison under the changed implementation or
measurement order requires a separate founder decision that binds its source
commit, command, image, dependency bytes and observation protocol. The T003
runner rejects this changed prototype under the old approval. The
current two-workstream corpus has one candidate wave and one path-overlap
wave; a scheduling advantage would need a separately reviewed workload and
admission contract where those schedules can differ safely. External human
validation and M2 closure remain pending.
