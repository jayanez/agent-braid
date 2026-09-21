# Spec Kit integration validation record

This file preserves the original integration validation record. Current day-to-day,
pull-request and evidence-boundary commands are defined in the
[validation profile guide](VALIDATION_PROFILES.md).

Local implementation validation on 2026-09-17. The Spec Kit foundation was
validated on `foundation/spec-kit-guardrails`; the open-tooling extension is
being validated on `strategy/open-tooling-foundation`. No push or remote CI
execution was performed.

## Executed controls

The foundation suite passed 38 tests. The open-tooling work adds analyzer,
benchmark, radar, and market-model cases; the final count is recorded by the
current CI run rather than treated as a fixed scientific metric. The pinned-tool
integration test passed all four configuration subcases. Regeneration check
reported zero changed files.

- Foundation validator: required files, Markdown links/anchors, JSON parsing,
  clause zero, 25 articles, ownership and licensing.
- Existing versioned contract corpus and all existing laboratory tests.
- New structural tests: missing/altered replica, deterministic/idempotent copying,
  stale/new authority fingerprints, approval reset, broken document/test/article
  references, absent mandatory evidence, changed evidence inputs, missing/stale
  integrations, legacy-command shadowing and incompatible constitution-sync.
- Pinned Spec Kit regeneration check and temporary Git repository matrix:
  Codex only, Claude only, both with Codex active, both with Claude active.
  Each exercises official init/install/use, restoration of selection, repeat
  generation, upstream overwrite detection, native metadata and real feature/plan
  template materialization. Dual setups compare effective command bodies exactly.
- Finite scientific controls CE1–CE5 and S3 product/braid checks.
- Offline radar provenance and milestone-review structure; no web freshness claim.
- Reproducible nested market scenarios with units, assumption labels, and
  incompatible-unit double-counting protection.
- Deterministic alpha analysis report, CLI behavior, nine synthetic software
  scenarios, zero false-safe classifications in that corpus, and published
  coverage, unknown, false-serialization, and pair-evaluation metrics.
- Editable six-slide market report plus PDF preview; visual review, overflow,
  package-integrity, geometry, and template-fidelity checks passed. Public
  redistribution of proprietary template material remains a separate review.
- The [pilot](../../specs/001-certificate-verifier-pilot/spec.md) records actual
  verifier/test evidence and exact input hashes independently of planned outcomes.
- Constitution matches baseline SHA-256
  `ff7196976a1736a639947c2ab26e8da157fef23c89ba9881312f2a36459964eb`.
  AIM/certificate schemas, legacy examples, lab algorithms and CODEOWNERS remain
  unchanged; the analysis report uses a separate `0.1.0-alpha` schema.

## Not executed or not established

No interactive Codex or Claude model session was started, and no independent
agent review or founder scientific approval is claimed. Both executables being
present does not establish authentication or authorize delegated sessions.
The guided prompts and expected review boundaries are in the pilot quickstart.
Windows and remote CI have not been exercised. The generic skill validator's
metadata mismatch is documented in the [guide](SPEC_KIT.md).

These are executable structural controls plus documented agent obligations;
neither class proves complete constitutional semantics or scientific correctness.
Human review of the integration, amendment proposals and claims remains distinct.
