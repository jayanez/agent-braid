# Certificate verifier: Spec Kit traceability pilot

## Scope

This retrospective specification exercises the existing bounded verifier, not
a new implementation. It changes no certificate, AIM, assurance or algorithm.
Canonical meaning is defined by the operational semantics and ADR 0005; see the
machine-readable authority inventory and article references in `assurance.json`.

## Requirements and acceptance

- REQ-001: Preserve distinct verified, unverified and rejected certificate outcomes.
  SC-001: Given the exhaustive corpus fixture, when the CLI verifies it, then it
  reports verified and exits zero. SC-002: Given unsupported formal proof evidence,
  when checked, then it stays unverified with nonzero exit, not falsely verified.
- REQ-002: Reject tampered evidence even when the attacker updates artifact hashes.
  SC-003: Given a forged outcome with a recomputed digest, when verification runs,
  then semantic replay rejects it.

Tests: `CertificateTests.test_cli_exit_status` and
`CertificateTests.test_rehashed_fake_outcome_is_rejected` in `tests/test_lab.py`.
Actual evidence is separate from these expected outcomes in `assurance.json`.

## Boundaries

Domain: integer-batch-v1 and the finite 0.2.0-draft fixture corpus. This does not
prove arbitrary agent confluence, validate Yang–Baxter for AI agents, implement a
formal proof checker or establish production suitability. No new hypothesis is
asserted. Live Codex and Claude exercises remain distinct from structural checks.
