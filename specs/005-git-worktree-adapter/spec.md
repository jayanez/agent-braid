# Git and worktree analysis adapter

## Scope

Add a deterministic, local and read-only Git adapter that converts stable commit
and worktree snapshots to AIM 0.2 records and delegates classification to the
existing analyzer.

## Requirements and acceptance

- REQ-001: Resolve a mandatory base and every commit source to immutable hashes;
  observe worktrees twice and reject unstable or unrelated sources.
- REQ-002: Preserve operation identity, dependencies, repository-relative
  resources and snapshot provenance without exposing absolute paths.
- REQ-003: Treat overlap conservatively and return unknown for partial,
  destructive, unsupported or explicitly uncertain effects.
- REQ-004: Keep `analyze` and `verify` compatible and emit the existing report
  contract with `executionAuthorization: false`.
- REQ-005: Publish a reproducible Git corpus with zero false-safe classifications
  relative to its declared dependencies and observed syntactic domain.

## Boundaries

The adapter performs no checkout, index update, merge, commit, network call,
agent execution or external effect. Path disjointness is assurance class 1 and
is not semantic commutation, merge safety, confluence or authorization.
