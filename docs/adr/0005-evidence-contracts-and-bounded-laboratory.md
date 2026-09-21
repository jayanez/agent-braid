# ADR 0005: Evidence contracts and bounded laboratory

- **Status:** accepted by the founder on 2026-09-16
- **Date:** 2026-09-15
- **Deciders:** Juan Antonio Yáñez García
- **Constitutional articles:** 3, 4, 6, 13, 14, 16, 20, 24

## Context

### Adoption record — 2026-09-16

The founder approved direct integration and publication of the implementation,
together with ADR 0004. Its adoption record documents the one-time exception to
the original dedicated-PR route. This acceptance does not promote finite-model
evidence into production guarantees or establish any pending mathematical claim.

Draft 0.1 cannot express separate coverage, verified evidence or execution
premises and accepts structurally valid but meaningless schedule claims.

## Decision

Preserve draft 0.1 bytes. Add versioned 0.2 contracts, separate producer claims
from consumer reports, and implement deterministic integer batches of at most
six operations. Replay checks a finite observation claim; external proof artifacts
are bound but remain unverified. Keep the lab and foundational validator on the
standard library; pin jsonschema 4.25.1 for development-only structural tests.

## Alternatives considered

Silent replacement breaks draft provenance. A bespoke general JSON Schema engine
increases the trusted surface. A production runtime or automatic residual
synthesis would expand the model before its premises have executable controls.

## Consequences

New interfaces are explicitly experimental and not automatically populated from
old records. The checker can reject false claims but cannot certify arbitrary
proof languages. Executable research files explicitly use AGPL-3.0-only; research
prose keeps CC-BY-SA-4.0. No operational authorization follows from a certificate.

## Validation

Require immutable legacy fixtures, structural positive/negative cases, semantic
mutation tests, replay reproducibility and all scientific controls. A separate
constitutional review of ADR 0004 precedes adoption of dependent changes.

## References

See [scientific integration](../theory/SCIENTIFIC_INTEGRATION.md) and the
[reference index](../../research/REFERENCES.md).
