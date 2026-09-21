# M0 exit-criteria matrix

This matrix is the review inventory for M0. Passing its executable checks does
not approve the milestone or establish the scientific claims listed as open.

| Exit criterion | Authority | Current artifact | Executable evidence | Human gate | Limits and deferred work |
|---|---|---|---|---|---|
| Core terms have testable working definitions | Articles 3, 13, 24 | `TERMINOLOGY.md`; bounded operational semantics | Repository validator; laboratory tests | Founder checks scope and terminology | Definitions remain experimental outside `integer-batch-v1` |
| Bounded interpreter, negative controls and scoped certificate checks run | Articles 4, 9, 10, 14 | Lab, CE1–CE5, S3 and certificate corpus | `tests/test_lab.py`; `research.lab.controls`; contract validator | Scientific review of actual outputs | Finite diagnostics, not production safety or general confluence |
| Independence and schedule-equivalence premises are explicit | Articles 2, 4, 6, 13 | T1 and T2 in operational semantics | CE1, CE3–CE5 and certificate replay tests | Review assumptions and observation boundary | T1/T2 are unmechanized proof sketches; contextual checking remains open |
| Constitutional proposal completed dedicated review | Clause zero; Articles 8, 13, 17, 18 | ADR 0004 and adopted Constitution | Constitution byte and article checks | Already approved in ADR 0004 | No new constitutional decision in this feature |
| Required effect domains are representable | Articles 5, 15, 16 | Portable workload fixtures | `M0ClosureTests.test_portable_workloads_cover_required_effects` | Review that examples do not imply execution | Real adapter effect coverage remains unverified |
| Multiple host-origin workloads use canonical concepts | Articles 1, 3, 7, 16, 24 | Code-agent and CI/deployment fixtures | AIM schema and identity/dependency/version tests | Review portability claim | Declarative examples, not captured third-party traces |
| Alternative schedules are host-neutral | Articles 2, 4, 9 | `integer-batch-v1` schedule enumeration | Complete topological-order tests | Review finite-domain boundary | No real agent or arbitrary interleaving |
| Open mathematical questions remain explicit | Clause zero; Articles 8, 10, 17, 18, 22, 23 | Research program, scientific integration and proof inventory | Link and required-statement checks | Review public wording | General confluence, contextual equivalence, Yang–Baxter and adapter correctness remain open |
| License, contribution and trademark policy are adopted | Governance; Article 21 | LICENSE, NOTICE, CONTRIBUTING and TRADEMARKS | Repository licensing validator | Founder controls policy changes | Formal trademark registration is outside M0 |
| Pilot and milestone decisions are explicit | Articles 13, 14, 19, 23 | Pilot assurance, two agent reports and founder review record | M0 closure validator | Separate scientific and closure decisions | External independent reproduction is deferred to the M0.5 research-preview gate |

## Evidence relationships

- **T1 independence:** CE2 demonstrates why non-atomic execution needs a separate
  refinement contract; CE4 preserves per-instance results; CE5 prevents a
  disjoint-write shortcut from silently discarding invariants.
- **T2 schedule equivalence:** CE1 refutes initial-state pairwise sufficiency;
  CE3 refutes terminal projection as a reusable contextual equivalence. The
  finite certificate verifier checks only declared schedules and observations.
- **S3:** the exhaustive finite group control checks conventions for a known
  braid operator. It is not evidence that agent operations satisfy Yang–Baxter.
- **Certificate verifier:** supported finite replay may be `verified`; an
  unsupported proof stays `unverified`; malformed or false evidence is rejected.

## Milestone boundaries

Independent third-party reproduction is required before a research-preview
proposal, not claimed by internal M0 closure. Review of product strategy, market
signals and the radar remains in M0.5. Independent reproduction of the analyzer
corpus and real Git/worktree benchmarking remain in M1. Privacy and security
review becomes blocking before accepting third-party traces; M0 uses only local,
synthetic fixtures.
