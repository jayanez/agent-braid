# Plan

Apply Articles 1–7, 13–16, 19, 20, 23, and 24. Keep the analysis pipeline
distinct from scheduling and execution. Use Python 3.12 with a standard-library
runtime core and document the decision in ADR 0007.

Accept AIM 0.2 records without altering AIM. Emit a separate alpha report schema.
Prefer unknown on incomplete coverage, transform/delete/deploy/call/emit effects,
or unsupported meaning. Test dependency, overlap, version, ordering,
determinism, malformed input, CLI behavior, and verifier delegation.

The initial benchmark is synthetic and pairwise. It measures reference-corpus
classification only and cannot establish production safety or complete semantic
coverage.
