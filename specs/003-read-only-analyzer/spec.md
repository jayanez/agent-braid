# Local read-only interaction analyzer

## Scope

Implement an alpha Python 3.12 CLI that analyzes AIM 0.2 records or a separate
analysis-input envelope and emits a versioned human or JSON report. Productize
the existing finite certificate verifier behind the same command surface without
changing its claims.

## Requirements and acceptance

- REQ-001: Exact declared dependencies and shared write-like resources become
  `ordered` or `conflicting`; partial coverage and external effects become
  `unknown`.
- REQ-002: Independent candidates carry evidence, constraints, uncertainty, and
  limits, and never authorize execution.
- REQ-003: Output is deterministic and valid against the independent
  `0.1.0-alpha` report schema.
- REQ-004: The nine-scenario software corpus has zero false-safe candidate
  classifications and publishes unknown and candidate rates.
- REQ-005: `verify` preserves the bounded verifier's verified, unverified, and
  rejected behavior.

## Boundaries

The analyzer uses exact strings and declared metadata. It performs no semantic
code analysis, Git operation, tool call, agent execution, or network access.
`independent-candidate` is not `commuting`, confluence, safety, or authorization.
