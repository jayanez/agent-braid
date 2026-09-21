# Governance

Agent Braid begins as a founder-led open research project.

## Founder

The founder and initial maintainer is **Juan Antonio Yáñez García (`@jayanez`)**. Repository policy, releases, constitutional amendments, licensing, and public claims require founder approval until a later governance model is adopted.

## Decision classes

Spec Kit feature records are subordinate to the canonical authorities. Its
constitution command drafts proposals only; it cannot approve or apply amendments.
See the [shared workflow](docs/development/SPEC_KIT.md). Hash snapshots and passing
structural checks do not constitute founder or human review approval.

| Decision | Required record |
|---|---|
| Editorial correction | Normal pull request or commit |
| Reversible implementation detail | Pull request with tests |
| Public API or schema change | Pull request, migration note, and versioning impact |
| Architectural choice | Architecture Decision Record (ADR) |
| Research claim | Evidence, reproducible artifact, and claim-level label |
| Constitutional amendment | Dedicated ADR and pull request referencing affected articles |
| License or governance change | Explicit founder decision and permanent repository record |

## Scientific integrity

Maintainers must:

- distinguish hypotheses, analogies, empirical findings, and theorems;
- disclose failed experiments and counterexamples relevant to published claims;
- identify observation boundaries and assurance levels;
- avoid presenting model-generated judgments as proofs;
- correct material errors publicly and promptly;
- preserve provenance for datasets, traces, benchmarks, and citations.

## Releases

A release must identify:

- the supported semantic/schema versions;
- the assurance levels implemented;
- known unsound or incomplete analyses;
- benchmark commit and environment;
- security-relevant changes;
- migration steps for breaking changes.

Software maturity and scientific validation are separate. Every future release
record SHALL declare `independent_validation` as `pending`, `completed` or
`not_applicable` under the [release validation policy](docs/releases/VALIDATION_POLICY.md).
A pending external reproduction does not block a research preview, milestone or
stable software release, but it blocks any claim of independent validation.
`not_applicable` cannot be used for a release carrying scientific or benchmark
claims. Repository visibility and release publication remain explicit founder
decisions.

Semantic versioning is intended once a public package or schema reaches its first stable contract.

## Licensing and project identity

The founder has adopted `AGPL-3.0-only` for software and executable materials
and `CC-BY-SA-4.0` for documentation and research. The authoritative path mapping
is maintained in [LICENSE](LICENSE). Changes to that boundary require a dedicated
ADR and explicit founder approval.

The Agent Braid name and branding identify the official project and are governed
separately by [TRADEMARKS.md](TRADEMARKS.md). Open-source copyright permissions
do not imply endorsement or permission to brand a fork as the official project.

## Conflicts of interest

Contributors should disclose commercial, academic, or competitive interests that materially affect a proposal, benchmark, or comparison. Disclosure does not disqualify a contribution; undisclosed influence damages the evidence trail.

## Future governance

Broader maintainer roles may be introduced after sustained contribution. Any change must preserve the Constitution, evidence standards, and founder attribution of the project’s origin.
