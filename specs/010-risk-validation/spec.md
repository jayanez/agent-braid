# Risk-based validation orchestration

## Purpose and scope

Reduce development feedback time without weakening Agent Braid's normative,
scientific, contractual or publication gates. A deterministic local orchestrator
will classify changed paths, explain the resulting validation plan and run the
smallest safe development profile. Complete pull-request validation and bounded
clean-room evidence remain separate gates at stable candidate boundaries.

This is an engineering and contributor-process feature. It does not change the
Constitution, public schemas, analyzer behavior, scientific claims, assurance
classes or approval authority. It does not infer semantic impact from source text
and it does not claim that path selection proves correctness.

## Authorities

Clause zero and Articles 9, 10, 13, 14, 19, 21 and 23 require honest evidence,
negative controls, measurable engineering and explicit limits. Governance keeps
human and founder decisions separate from executable checks. ADR 0006 governs the
shared Spec Kit integration; ADR 0009 governs transparent validation status. ADR
0011 will record the subordinate validation-tier decision.

## Requirements and acceptance scenarios

### REQ-001 — Classification is deterministic, inspectable and conservative

Given a base revision and a set of tracked or untracked changed paths, when the
orchestrator plans validation, then it must emit the selected domains, reasons,
commands and deferred boundary gates deterministically. Any unknown path must
fall back to exhaustive sensitive validation rather than being silently skipped.
See SC-031.

### REQ-002 — Ordinary development receives targeted fast feedback

Given an editorial, runtime, contract, laboratory, strategy or governance change,
when the quick profile runs, then invariant checks and the affected domain tests
must execute without running unrelated clean-room or multi-agent integration
matrices. Failures must propagate a nonzero exit status. See SC-032.

### REQ-003 — Pull-request candidates retain repository-wide coverage

Given a stable candidate, when the PR profile runs, then the full unit suite,
repository and contract validators, scientific controls, Spec Kit structure and
render checks, release/publication validators, Constitution replica and whitespace
must run. The profile must not capture, freeze or approve evidence. See SC-033.

### REQ-004 — Sensitive changes activate their specialist controls

Given a change to normative authorities, public contracts, scientific algorithms,
supply-chain inputs, validation policy or Spec Kit generation inputs, when it is
classified, then the plan must be marked sensitive. Changes capable of altering
Codex or Claude integration output must additionally run the pinned solo/dual
integration matrix; unrelated paths must not. See SC-034.

### REQ-005 — Evidence boundaries remain explicit and non-automatic

Given a milestone closure, release, publication or scientific evidence candidate,
when validation is planned, then ordinary profiles must identify the applicable
clean-room or evidence procedure as a separately authorized boundary gate. No
successful quick, PR or sensitive profile may be represented as clean-room
reproduction, human review, founder approval or independent validation. See SC-035.

### REQ-006 — CI preserves gates while reducing critical-path latency

Given a push or pull request, when CI runs, then fast invariant, complete test,
governance/science and Spec Kit jobs must be separable and parallelizable. The
expensive solo/dual Spec Kit matrix must be conditional on its owned inputs or an
unknown-path fallback. A skipped specialist job must remain distinguishable from
a passing job. See SC-036.

## Scientific boundaries and compatibility

Path classification is a conservative build optimization, not dependency analysis
or scientific evidence. It can select executable checks but cannot determine
constitutional compliance, scientific truth, production safety or reviewer intent.
Unknown paths fall back to the sensitive profile, and every PR candidate retains a
repository-wide suite. Existing contracts, closure records and clean-room scripts
remain unchanged and authoritative for their own evidence boundaries.

## Evidence and unresolved questions

Obtained evidence consists of classifier unit tests, negative fallback tests,
command-failure propagation tests, workflow inspection, pinned integration
regeneration and the complete repository suite. On 2026-09-19 the founder accepted
ADR 0011, the four validation moments and the conservative fallback rules, and
approved the bounded local evidence. The decision is recorded separately from the
future commit binding required to promote the assurance record to formal frozen
approval. GitHub-hosted execution remains unexecuted while billing blocks Actions.
