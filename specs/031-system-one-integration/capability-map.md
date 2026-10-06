# Draft capability register

Every row is planned, opt-in and heuristic; no consumer is enabled by this document.
Priority order reflects bounded compatibility and evaluability, not assumed accuracy.

| Priority | Capability | Current integration target | Fallback and hard boundary |
|---|---|---|---|
| P0 | Analyzer selection / analysis-depth recommendation | analysis.py / git_replay.py | Existing analysis; mandatory checks cannot be skipped |
| P0 | Candidate verifier-work prioritization | structured_exchange.py / SPEC-019 eligible contexts | Existing structural rule and unchanged verifier |
| P1 | Effect discrepancy review | git_adapter.py / AIM metadata | Keep both evidence sources, unknown remains unknown |
| P1 | Diagnostic / counterexample triage | git_counterexamples.py | Actual replay/reduction; score cannot establish divergence |
| P1 | Model and tool shortlist | New optional host advisor | Registry-only choices; deterministic argument validation |
| P1 | Answer adequacy / rubric scoring | New optional host advisor | System 2 or defer; outcome is human proxy unless observed |
| P2 | Constraint-admissible scheduling priority | runtime_scheduler.py | Existing ready/dependency/isolation rules; no new waves |
| P2 | Supported execution policy recommendation | runtime_policy.py | Same fixed-patch domain and independent operator grant |
| P2 | Normalizer selection recommendation | Registered observation contract | Pinned normalizer verified deterministically, model never equivalence oracle |
| P2 | Trace categorization / evidence search | New advisory trace adapter | Certificate bytes and consumer verification unchanged |

No arbitrary agent planner, tool executor, deployment, source promotion, remote
service or generalized conflict-proof feature is introduced. Future consumers need
their own capability version, supported population, group evidence and explicit
fallback. Tool guardrails are triage, not authentication or complete safety filters.
Observe disagreements without automatically training on host/self-generated labels.
