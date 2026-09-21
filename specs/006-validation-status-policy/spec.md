# Transparent validation status policy

## Scope

Separate software maturity from scientific validation and replace external
reproduction as a publication blocker with a visible, structured validation
status. This feature does not publish a release, change repository visibility or
approve scientific evidence. ADR 0009 remains the accepted policy decision;
versioned schema implementations of that policy require their own evidence and
technical review.

## Requirements and acceptance

- REQ-001: Release records distinguish executable checks, internal clean-room
  reproduction, founder scientific review and external independent validation.
- REQ-002: Pending validation discloses conflict of interest, links a runnable
  protocol, invites external reproduction and cannot claim independent validity.
- REQ-003: Completed validation binds an identified external reviewer and
  repository evidence; `not_applicable` is limited to releases without scientific
  or benchmark claims.
- REQ-004: Historical M0 decisions remain immutable while prospective M0.5 and
  release policy can be superseded through an explicit founder decision.
- REQ-005: A material release-record contract migration increments its version,
  documents compatibility, rejects the superseded version and receives fresh
  executable evidence and technical review without reopening ADR 0009 itself.

## Boundaries

Structural validation cannot authenticate a reviewer, establish independence,
approve a release or make scientific conclusions. Stable software denotes
compatibility and support, not safety, truth or external validation.
