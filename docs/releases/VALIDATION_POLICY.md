# Release validation policy

**Status:** adopted by explicit founder decision in ADR 0009 on 2026-09-18

This policy keeps software maturity separate from scientific validation. A
research preview or stable software release may be useful and supported without
having been reproduced by an independent third party.

## Evidence gates

| Gate | Meaning | Does not establish |
|---|---|---|
| Executable checks | Recorded checks passed for their stated inputs | Scientific truth or human approval |
| Internal clean-room reproduction | Frozen evidence reran outside the development worktree and environment | Independence from the project founder |
| Founder scientific review | The founder accepted the bounded evidence and limits | External or peer validation |
| Independent validation | An identified external reviewer reproduced bound evidence | General validity outside the reviewed domain |

## Release records

Every future release record must conform to the repository's release-validation
contract and declare exactly one status:

- `pending`: no qualifying external reproduction is recorded;
- `completed`: an external reviewer and immutable evidence are recorded;
- `not_applicable`: the release carries no scientific or benchmark claim and
  gives a non-empty rationale.

A pending release must say that its evidence is internally reproduced, disclose
the founder's conflict of interest, and link to a runnable reproduction protocol.
It must invite independent reproduction and must not use wording that claims or
implies independent validation.

Contract `0.2.0` replaces the provisional `0.1.0` string-valued completed
reviewer with a structured external-reviewer identity, affiliation, externality
declaration and conflict-of-interest statement. Pending `0.1.0` records migrate
by updating their version because their status-specific fields are unchanged.
No completed `0.1.0` release record was published by this repository.

Stable software describes supported interfaces, compatibility and maintenance.
It does not upgrade empirical evidence, prove safety, or imply independent
scientific validation.

## Historical records

M0 records remain frozen descriptions of the decisions made at closure. The
[supersession note](M0_POLICY_SUPERSESSION.md) records the later prospective
change instead of rewriting historical evidence or approval records.
