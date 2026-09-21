# ADR 0009: Transparent validation status

## Status

Accepted by explicit founder decision on 2026-09-18. Acceptance adopts the
validation-status policy; it does not approve a release, change repository
visibility, authenticate an external reviewer or establish a scientific result.

## Context

Agent Braid needs external scrutiny, but requiring an independent third party
before every research preview or stable software release would make publication
depend on a community that does not yet exist. Removing the distinction entirely
would overstate founder-led evidence and weaken Articles 13, 14, 19, 21 and 23.

Software stability and scientific validation answer different questions. A
stable release can promise supported interfaces and compatibility without
claiming that its scientific conclusions were independently reproduced.

## Decision

Use four separate gates:

1. executable checks establish only their recorded structural or finite result;
2. an internal clean-room reproduction reruns frozen evidence without reusing the
   development worktree, environment or caches;
3. founder scientific review approves only the stated scope and limits; and
4. independent validation requires an identified external reviewer and bound
   reproduction evidence.

Internal clean-room reproduction plus explicit founder approval may support a
research-preview proposal. Independent validation is invited but does not block
milestone closure, repository visibility or a stable software release. It does
block any claim that the project or release is independently validated.

Every release record must declare `independent_validation` as `pending`,
`completed` or `not_applicable`. `pending` records must disclose the internal
reviewer's conflict of interest and link to a reproduction protocol. `completed`
records must identify an external reviewer and bind their evidence.
`not_applicable` requires a rationale and may not be used for a release carrying
scientific or benchmark claims.

## Alternatives

- Keeping independent reproduction as a publication gate preserves a strong
  signal but can prevent scrutiny and community formation indefinitely.
- Dropping validation status removes friction but makes internal and independent
  evidence too easy to conflate.
- Treating stable software as scientifically validated confuses interface
  maturity with evidence quality.

## Consequences

Research previews and stable releases may precede independent reproduction, but
their status and limitations remain visible. Historical M0 records are not
rewritten; prospective documents may note that this ADR supersedes the earlier
gate after founder acceptance. Repository visibility, release publication and
scientific approval remain separate explicit founder decisions.
