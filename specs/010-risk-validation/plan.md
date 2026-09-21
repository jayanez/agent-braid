# Implementation plan

## Technical context and scope

Add a dependency-free Python 3.12 validation orchestrator. It inspects committed,
staged, unstaged and non-ignored untracked paths relative to an explicit Git base,
maps them to owned validation domains and produces deterministic text, JSON or
GitHub-output plans. It executes commands directly without a shell and propagates
the first failing result. Existing validators remain the authorities for their
domains.

The workflow will separate classification, invariant, complete-test,
governance/science and Spec Kit jobs. The complete suite remains mandatory for PR
candidates. Only the expensive temporary-repository Spec Kit matrix is path-gated.

## Constitution check before research

Clause zero and Articles 13, 14 and 17 prohibit presenting selection or passing
checks as proof. Articles 9, 10, 19, 21 and 23 require negative controls,
measurable performance and independent value at each phase. No constitutional
MUST requires every validator after every edit. Governance permits reversible
implementation changes through a tested PR; the operational policy is recorded
in proposed ADR 0011 and does not amend approval authority.

## Research, assumptions and alternatives

See `research.md`. Measured locally on 2026-09-19, repository validation took
about 0.12 seconds, contract validation 0.14 seconds, scientific controls 0.02
seconds, affected runtime tests 10.8 seconds, structural Spec Kit validation 10.9
seconds, the 105-test suite 44.9 seconds and the temporary-repository Spec Kit
matrix 96.5 seconds. These observations describe one machine and are not
performance guarantees.

Always running everything was rejected because it conflates development feedback,
PR acceptance and evidence reproduction. Skipping repository-wide validation was
rejected because path maps are incomplete dependency approximations. Third-party
path-filter actions were rejected to avoid another supply-chain dependency.

## Design and compatibility

- `scripts/validate_change.py` owns a conservative, ordered path map and command
  registry. Unknown paths select the sensitive fallback.
- `quick` runs invariant checks plus affected-domain tests. `pr` runs the complete
  repository gate once on a stable candidate. `sensitive` runs `pr` plus any
  specialist gate selected by the changed paths.
- Paths that can change generated Codex or Claude integrations activate the pinned
  solo/dual Spec Kit matrix. Normative, scientific, contract, validation-policy and
  supply-chain paths are sensitive even when that matrix is irrelevant.
- Evidence-producing clean-room scripts remain explicit, feature-specific commands;
  the orchestrator reports them as deferred boundary gates and never runs them as a
  side effect of an ordinary profile.
- CI uses the classifier only to gate specialist work. Core invariants and the full
  unit suite remain unconditional for PRs and pushes.
- AIM, certificates, assurance levels, analyzer commands and report schemas are
  unchanged.

## Validation strategy

- REQ-001/SC-031: deterministic output and unknown-path fallback tests.
- REQ-002/SC-032: domain mapping, exclusion of unrelated expensive work and mocked
  command-failure propagation tests.
- REQ-003/SC-033: PR plan inventory test against all required gates.
- REQ-004/SC-034: positive and negative specialist-trigger tests.
- REQ-005/SC-035: boundary classification and non-authorizing wording tests.
- REQ-006/SC-036: workflow structure test for parallel jobs, unconditional full
  suite and conditional Spec Kit integration.

After targeted tests, run the PR profile and the real pinned integration matrix
because this implementation changes the shared guardrail template. Record actual
outputs as bounded engineering evidence. Do not freeze or approve the record in
this implementation turn.

## Constitution check after design

The design changes when checks run, not what their passing means. Unknown paths
fail closed to a stronger profile; stable PR candidates retain the complete suite;
and clean-room, human, founder and independent validation remain separate. No
scientific claim, public contract or constitutional text changes.

## Human review and unresolved decisions

The founder accepted ADR 0011, the four validation moments, the conservative rules
and the bounded local evidence on 2026-09-19. The substantive review is complete;
formal assurance promotion remains pending only because approval must bind a clean
historical candidate commit. GitHub Actions cannot be reported as executed while
billing blocks hosted runs. The path map must evolve with the repository; unknown
paths remain deliberately covered by the conservative fallback.
