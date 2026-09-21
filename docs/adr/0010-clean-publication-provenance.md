# ADR 0010: Clean publication and portable provenance

## Status

Accepted by explicit founder decision on 2026-09-19. This decision authorizes
the local architecture and implementation. It does not authorize a remote rename,
repository creation, push, visibility change, tag or release publication.

## Context

The current Agent Braid tree is redistributable, but private Git history contains
an earlier report derived from a proprietary template. M0, M0.5 and M1 assurance
records also bind evidence to private commit objects. Making the repository public
would disclose the historical derivative; discarding the records would obscure
the project's scientific history.

## Decision

Publish the research preview from a new Git root generated from one exact private
commit. Preserve the private repository as an inactive internal archive and make
the clean public repository the only active development line.

The export carries a canonical per-file manifest identifying the private source
commit and tree. Public validation checks exported bytes and fresh public-root
reproduction evidence. It reports private ancestry as unavailable and does not
represent inherited internal decisions as independently or publicly reproduced.

Machine-local absolute paths in inherited evidence are deterministically redacted
only in the public export. SHA-256 references to transformed records are rebound
to the published representations. The manifest discloses each affected path, its
private-source digest, published digest and applied rule. Original evidence bytes
remain immutable in the private archive; the public representation is explicitly
not claimed to be byte-identical to them.

Historical milestone validators bind candidate-to-closure intervals rather than
comparing frozen candidates with a perpetually moving HEAD. The private clone and
public clone remain physically separate; the private clone never receives the
public remote.

## Alternatives

- Direct visibility change exposes every reachable private object.
- History rewriting is destructive and changes evidence-bound commit identities.
- A permanent public mirror creates two active authorities and synchronization
  risk.
- Removing internal records weakens transparency.

## Consequences

The public history begins at the research preview and cannot verify private
ancestry. The manifest and fresh reproduction make that boundary inspectable but
do not authenticate the founder or validate scientific claims. Redacted evidence
retains inspectable results but cannot substitute for access to the archived
original bytes. Publication needs separate founder authorization and produces
`v0.1.0-alpha.1` with
`independent_validation: pending`. No package is published and no runtime or
scientific contract changes.
