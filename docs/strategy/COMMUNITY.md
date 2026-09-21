# Community and impact strategy

## Objective

Build an international open research and engineering community that can inspect,
reproduce, challenge, and extend Agent Braid. Adoption quality matters more than
download volume.

## Contribution ladder

1. Re-run the reference corpus and report the environment and commit.
2. Contribute a minimized counterexample or a trace with a declared observation
   boundary.
3. Add a workload family and its expected conservative classifications.
4. Implement an adapter that preserves AIM identity, effects, versions, hashes,
   and uncertainty.
5. Submit a scoped scientific claim with reproducible evidence and peer review.

## Impact metrics

| Dimension | Initial metric | Guardrail |
|---|---|---|
| Correctness | False-safe classifications in the public corpus | Must remain zero; corpus coverage is reported alongside it |
| Diagnostic value | Unknown rate and false serializations | Neither is optimized without preserving the safety boundary |
| Reproducibility | Independent reproductions with environment and commit | Maintainer reruns do not count as independent |
| Interoperability | Maintained adapters and workloads | Adapter count is not evidence of semantic correctness |
| Community | Repeat contributors and reviewed counterexamples | Stars and downloads are contextual signals only |
| Research | Reproducible negative and positive findings | Citations do not upgrade claim level automatically |

## Operating cadence

- Weekly read-only radar: candidates for human triage; no repository changes.
- Monthly deep review: a human-reviewed pull request records adopted decisions.
- Milestone review: mandatory even when the monthly review is recent.
- Milestone communication: update the international trends report only after
  evidence and review, not from weekly signals.

Public communication must identify the applicable claim level and must not imply
production safety, general confluence, or general Yang–Baxter validity.
