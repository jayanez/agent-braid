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
| 2 | 116.77 ms | 127.05 ms | 153.47 ms | 7.28% (95%: 2.70% to 11.16%) | 23.05% (95%: 17.71% to 28.76%) |
| 3 | 192.62 ms | 195.63 ms | 226.04 ms | 5.66% (95%: -2.76% to 8.25%) | 15.05% (95%: 9.99% to 17.61%) |

These percentages are medians of **paired fractional improvements**, rather
than ratios of the displayed lane medians. The three-operation serial interval
includes zero. **The 10% goal is not met.** Both path-only and candidate
schedulers form the same single wave on these disjoint-path fixtures, so the
gain against the frozen path baseline reflects fewer Git operations in the
implementation, not an advantage in scheduling decisions.

The raw report was produced with Linux ARM64 image
`sha256:edddb1cbcbccb0e1af6505f9ff9938905da6f79303c97d1d12092ef61508f005`,
Python 3.12.13 and Git 2.47.3, offline with two CPUs, 2 GiB memory and 512
processes. Its SHA-256 is
`8e08c0e49fcb9f3f2b777a819e8d297cffa2ae448a4e1417efc6e95436cc3fce`.
The script verifies frozen module SHA-256
`3daf9c4ae946ab9a59fb4c2711492468ffdb6455a0bf04f6318a99b7664db860`.
The measured candidate module SHA-256 is
`762ebfcc6246ab3b143e13b9a4bd3315c698972bf65e1ee00e8f892aea85d0a3`;
the benchmark script SHA-256 is
`819fcd9e667fa0f277004290f867b30d615a2ffe511201fe81711b9ee122fd8a`.
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
