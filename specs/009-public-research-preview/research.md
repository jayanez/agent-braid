# Research and decisions

## Selected topology

The current private repository will be renamed
`jayanez/agent-braid-private-archive` and retained as an inactive internal record.
A new `jayanez/agent-braid` will be created from a clean root and become the only
active development repository. `develop` will be the default contribution branch;
`main` will represent releases. Both start at `v0.1.0-alpha.1`.

The private clone must never receive the public remote. A separate clean workspace
is required so an accidental `push --all` cannot transfer private objects.

## GitHub behavior considered

Changing a private repository directly to public exposes all of its commits. A
mirror push also copies every ref and object reachable from those refs. Neither is
compatible with the unresolved historical derivative. A new repository initialized
from exported files avoids that disclosure boundary.

## Evidence portability

Historical assurance records refer to private commits. The public clone cannot
cryptographically reconstruct their ancestry and must not claim it can. The
manifest therefore proves only that the published files match the selected export
payload. A fresh reproduction bound to a public commit supplies executable evidence
for the released bytes. The internal closure decisions remain attributed historical
records with an explicit availability limit. Their public copies redact
machine-local absolute paths and rebind dependent digests deterministically. The
manifest exposes those transformations; original bytes remain only in the private
archive and are not claimed to be reconstructible from the public root.

## Alternatives rejected

- Making the existing repository public exposes the prohibited history.
- Rewriting the private repository is destructive and invalidates commit-bound
  records without solving their public interpretation.
- Maintaining two active repositories risks divergent authorities and releases.
- Omitting historical records reduces transparency and prevents readers from
  understanding how the current foundation was reviewed.

## Limits

Git object and SHA-256 integrity do not authenticate the founder, establish legal
rights beyond the recorded license analysis, validate scientific conclusions or
make internal review independent. Secret scanning is bounded pattern checking, not
proof that no sensitive information exists.
