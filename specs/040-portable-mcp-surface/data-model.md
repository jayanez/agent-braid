# Tooling data model proposal

These are feature-local proposed models. They do not amend versioned schemas or
constitute accepted public API. Implementation PR adds reviewed schemas/tests.

## AnalyzeWorkRequest

`kind`: aim or git. `request`: existing AIM analysis input or
git-analysis-request 0.1.0-alpha. Worktree analysis uses the existing Git
`source.kind = worktree` branch rather than another semantic model.
Unknown fields/kinds refuse. Keep existing observations/partial coverage.

For Git requests, canonical repository must equal the configured root. Each
commit resolves before observation; each worktree must be in an explicitly
configured canonical worktree allowlist and share the source Git common directory.
Default allowlist contains only the selected root. A sibling worktree requires
an operator-selected entry, never a tool argument expanding access.
Double-snapshot/point-of-use checks refuse drift. Worktree snapshots are content
fingerprints, not immutable Git commits or evidence of undeclared effects.

Initial envelope bounds: at most 32 operations, 256-byte operation identifiers,
1 MiB serialized request, 256 KiB inline output and maximum nesting depth 32.
Existing stricter Git command/resource bounds remain authoritative. These new
presentation/input limits may refuse larger valid core requests; document this
as transport coverage, never weakening core semantics.

## ToolingResult

`schemaVersion`: agent-braid-tooling/v0.1; `operation`: advertised tool;
`status`: ok/refused/unknown/error; `summary`: bounded string;
`result`: complete unchanged core result or a typed hash-bound artifact reference
to it; `evidenceRefs`: owned artifact IDs;
`limits`: nonempty domain limitations; `provenance`: exact input identity,
candidate/runtime/schema versions and observation contract.

Adapter ok means the invocation returned a valid core result. It does not turn a
failed verifier or unknown classification into a positive domain verdict.
Summary must expose the core outcome. Malformed adapter/transport input has a
protocol error; an admitted but refused operation uses an error/refusal result
with the reason. Neither case includes a success marker.

Artifact references use a distinct tagged schema branch; never confuse a
reference with the core JSON object. Bounded resource chunks preserve hashes,
offset/total length and exact bytes for reconstruction. Inline limit is 256 KiB,
chunk limit 256 KiB, maximum total artifact 8 MiB (existing stricter core bounds
remain). Refuse requests expected to exceed admitted resource bounds before
effects. Report-storage/rendering failure after execution must expose the actual
run identity/outcome and recovery/verification path, never pretend no effect.
Read-only analysis artifacts may live in bounded server memory; durable writes
require an explicitly selected owned output destination and receipt.

## EvidenceRef and RunInventory

EvidenceRef carries artifact ID, hash, media type, size and owned resource URI.
RunInventory maps bounded opaque run IDs to already-owned paths and exact saved
policy plan/evidence identities. Resource IDs do not replace legacy tool arguments.
Validate loaded plan/artifact hashes and containment each time; missing inventory
cannot discover arbitrary host files. Do not include grant-store content or grant
secrets in evidence. Expose only the minimum checked grant identity/scope.

## InstallationReceipt

Receipt includes bundle/version/hash; host/build; user/project scope; configured
roots; selected executable/arguments; before/after hashes and exact owned entries;
backup location; operation/outcome and residuals. Do not include secrets.
Modified bytes are a conflict, not permission to overwrite.

## ObservationReceipt

Separate evidence types: source-structure, synthetic-control, protocol-peer,
actual-host and clean-room. Fields bind registration, host/model/protocol/SDK/OS,
candidate/assets/inputs/outputs, actual commands/tool events, outcomes, cost
availability and limits. The SPEC-044 protocol controls registration and analysis.
