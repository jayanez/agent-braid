# M2 parallel Git preparation performance follow-up

The founder accepted SPEC-013 T006 at commit
`60d6bcaba7245e9864298321b1038cddfde6fd9e` as a bounded, internally
reviewed **negative performance result**. Its two completed real-corpus runs
were slower than serial. This follow-up does not replace or revise that record.

## Goal and method

The priority M2 goal is a reproducible median reduction of at least 10% in
total Git preparation time against both an equally optimized serial lane and
a timed path-overlap baseline. A seeded, paired bootstrap 95% interval must
also exclude zero improvement for each comparison. Tree identity, source
immutability, fail-closed classifications and resource limits remain gates.

`scripts/benchmark_m2_parallel_preparation.py` creates deterministic two-
and three-operation synthetic Git repositories. In the pinned Linux ARM64
image, it runs 30 paired samples per scenario, alternates current candidate
versus serial lane order, and alternates current versus baseline process order.
It retains each timing and every tree check in the [raw report](evidence/m2-parallel-preparation-synthetic-30.json).
The fixture base is `e1b19da2718932a1a63e190525deed6f276d2dbe`; its
operation commits are `cf8da53196ec1d44a1bc8aa5e950a93c811e5d0a`,
`a7532ab394f970ee1842df45054342d8f4031e37` and
`9fd2e051b2fe6e05f3da81877259f2f43dc58823`, each on a distinct
tracked path. The two-operation scenario omits the third commit.
The path baseline uses the byte-verified T003 prototype module at
`60d6bca`, with a conservative tracked-write overlap scheduler. The current
prototype avoids merging the first operation into its own base and avoids a
final redundant tree lookup. It still uses private Git objects and compares
candidate and serial trees. The benchmark executes Git-only synthetic fixtures;
it runs no project test command or live agents.

## Observed result

| Operations | Candidate median | Serial median | Path median | Paired gain vs serial | Paired gain vs path |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2 | 123.33 ms | 128.21 ms | 158.67 ms | 4.84% (95%: 1.66% to 9.06%) | 22.09% (95%: 16.24% to 25.25%) |
| 3 | 192.45 ms | 213.65 ms | 234.28 ms | 6.45% (95%: 3.31% to 12.34%) | 18.34% (95%: 12.01% to 20.61%) |

These percentages are medians of **paired fractional improvements**, rather
than ratios of the displayed lane medians. **The 10% goal is not met.** Both
path-only and candidate schedulers form the same single wave on these
disjoint-path fixtures, so the gain against the frozen path baseline reflects
fewer Git operations in the implementation, not an advantage in scheduling
decisions.

The raw report now retains the timing of patch preparation, fixture commit
materialization and tree integration for every lane in every sample. These are
median paired candidate-minus-baseline differences in milliseconds; negative
values favor the candidate:

| Operations | Baseline | Patch preparation | Commit materialization | Tree integration |
| --- | --- | ---: | ---: | ---: |
| 2 | Serial | -7.33 | +0.66 | -0.85 |
| 3 | Serial | -11.35 | -0.32 | -0.87 |
| 2 | Path overlap | -0.61 | +0.69 | -34.46 |
| 3 | Path overlap | +1.03 | +0.07 | -39.50 |

The candidate and serial lanes issue the same 10 Git commands for two
operations and 16 for three. Their measured gain comes from concurrent patch
preparation; commit materialization and tree integration remain mostly serial.
Against the frozen path baseline, the candidate saves three Git commands in
integration, explaining most of that larger gain. The candidate integration
phase itself has a 50.80 ms median for two operations and 92.22 ms for three;
it limits the effect of parallel patch preparation on total lane time. These
phase medians are descriptive and need not add up to the median total.

The raw report was produced with Linux ARM64 image
`sha256:edddb1cbcbccb0e1af6505f9ff9938905da6f79303c97d1d12092ef61508f005`,
Python 3.12.13 and Git 2.47.3, offline with two CPUs, 2 GiB memory and 512
processes. Its SHA-256 is
`74462a5be3468c13bfeed9a8c1ca11c0cc53cf679125a29d2bad5169a3ce3a38`.
The script verifies frozen module SHA-256
`3daf9c4ae946ab9a59fb4c2711492468ffdb6455a0bf04f6318a99b7664db860`.
The measured candidate module SHA-256 is
`762ebfcc6246ab3b143e13b9a4bd3315c698972bf65e1ee00e8f892aea85d0a3`;
the benchmark script SHA-256 is
`98ac65b18789a0d7823bcec3920326f67a89d30109bc5d58578cd53a6968ca54`.
Reproduction runs that script with `--samples 30`, the byte-verified T003
module passed as `--frozen-module`, and an explicit `--output` path in the
same pinned, offline container limits.

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
