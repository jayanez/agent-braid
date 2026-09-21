# Implementation plan

## Technical context and scope

Implement a dependency-free Python 3.12 publication toolchain around Git CLI.
The private repository remains the authority for internal historical ancestry;
the clean public repository verifies current bytes and fresh public-root evidence.
The export has a new root and cannot silently claim that private commit objects are
present. Remote creation and visibility remain a separately authorized final step.

## Constitution check before research

Clause zero and Articles 13, 14 and 17 prohibit evidence or publication wording
from upgrading internal reproduction to independent validation or a theorem.
Articles 19, 21, 23 and 25 require measurable, reproducible artifacts and preserve
the engineering/research feedback loop. Governance requires explicit founder
approval for release and public claims. The license map and third-party notice
require a clean export while the historical derivative remains unresolved.

## Research, assumptions and alternatives

See `research.md`. A direct visibility change exposes all private Git objects and
is rejected. A filtered rewrite changes every evidence-bound commit and remains a
history operation. A second active mirror creates permanent synchronization risk.
The selected design archives the private repository and makes a clean public root
the only active development line.

## Design and compatibility

- Add immutable closure anchors containing candidate, closure commit and closure
  tree for M0, M0.5 and M1. Validate only that historical interval and require the
  closure commit to remain an ancestor of the private HEAD.
- Generate `docs/releases/public-export.json` with contract version `0.1.0`, exact
  source commit/tree, policy flags and a sorted `{path, sha256, size}` inventory.
- Redact machine-local absolute paths in the exported copy only, recursively
  rebind SHA-256 references to transformed public records and disclose source and
  published hashes plus transformation rules in the manifest.
- Export with `git archive` into a new empty directory. Refuse the source root,
  nonempty destinations, symlinks, non-UTF-8 paths and unavailable commits.
- Portable validation is activated only when the manifest is present in the root
  commit of a root-history repository. It verifies current exported bytes and
  reports private ancestry as unavailable; it never reports historical closure
  provenance as re-executed.
- Preserve existing public contracts. The new manifest is governance metadata,
  not an AIM, certificate, analyzer or execution contract.

## Validation strategy

SC-026 covers closure interval stability and tampering. SC-027 covers deterministic
export, redaction, digest rebinding plus unsafe inputs. SC-028 covers portable
integrity, sensitive-path rejection and bypass resistance.
SC-029 covers fresh reproduction, stale evidence and overclaims. SC-030 remains a
structural readiness check until the founder authorizes remote mutation. Capture
one evidence artifact with commands, environment and limits; keep remote results
separate until actually executed.

## Constitution check after design

The design exposes less evidence than the private repository and says so. It does
not weaken the Constitution, replace scientific review with hashing, change
assurance classes or make the research hypothesis a product requirement. The
public reproduction establishes only that the exported code and controls rerun.

## Human review and unresolved decisions

ADR 0010 requires explicit founder acceptance. After a clean candidate, the
founder separately reviews the local publication evidence. Rename, repository
creation, push, visibility, branch rules, tag and GitHub prerelease require one
final explicit authorization listing those operations. GitHub Actions remains an
unexecuted external check while account billing blocks jobs.
