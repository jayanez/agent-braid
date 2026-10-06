# Synthetic recorded metadata import 0.1.0-experimental

This additive interface uses the fixed `generic-metadata-v1` mapper. Its
[request contract](contracts/0.1.0-experimental/trace-import.schema.json) and
[provenance contract](contracts/0.1.0-experimental/trace-provenance.schema.json)
are experimental feature-local contracts. Existing AIM `0.2.0-draft`, analysis
report `0.1.0-alpha`, analyzer rules, Git adapters and runtime contracts retain
all existing behavior. No migration of current analyzer users is required.

The [synthetic fixture](fixtures/generic.json) pins two disjoint writes; its
[independent direct-AIM baseline](fixtures/direct-aim.json) pins the expected
mapping. Input is one local UTF-8 JSON file, at most 1 MiB, 64 operations, 512
events, nesting depth 16 and metadata strings of 256 characters. Dynamic mapper
plugins, bodies, prompts, credentials, grants, execution directives and arbitrary
extension dictionaries are excluded. Tokens are restricted structural metadata;
this allowlist does not claim arbitrary secret detection. Only explicitly
synthetic input is admitted. Sanitized real input is still real and is rejected.

## Identity, digest and semantic mapping

| Source field | Mapping or boundary |
|---|---|
| `definition.id`, `definition.digest` | Preserved source definition identity and content digest; conflicting digest for one ID rejects |
| `instanceId`, `attemptId` | Preserved verbatim; one attempt per instance; duplicate instance/attempt rejects |
| `inputDigest` | Preserved source input-content digest; no missing argument body is invented |
| `dependencies` | Explicit edges only; omission records loss and unknown coverage; cycles/dangling/self edges reject |
| `readVersions` | Explicit nonnegative integer versions only; missing read resource version records loss and unknown coverage |
| `effects.declared/inferred/observed` | Channels preserved; omission records loss and unknown coverage |
| `effects.coverage` | Declared status/domain/method retained; missing semantic coverage lowers to unknown |
| lifecycle events | Retained with source instance/attempt ownership; timestamps establish no edges; non-completion or effectless events lower to unknown |
| AIM evidence | Mapper adds class 0 declared metadata evidence; lifecycle does not raise assurance |

`source.contentDigest` is the source-declared SHA-256 of canonical
`{"operations": ..., "events": ...}` recorded metadata. The importer checks it.
Definition and input digests identify source content whose bodies are deliberately
absent; the importer preserves those declarations and cannot verify the absent
bodies. `sourceFileDigest` hashes admitted raw UTF-8 bytes locally and is labelled
`local-sha256-raw-file`. Projection/report digests hash the exact deterministic
artifact bytes locally. Local transformations never replace missing source
content digests. No circular hash claim is made: provenance binds the report,
source and projection; the existing report binds projection through its existing
`inputDigest` without acquiring a new provenance field.

Unknown optional semantics remain bounded loss codes and conservative coverage.
Multiple attempts, generic extensions and lifecycle shapes outside the fixed
allowlist reject rather than silently flattening. Only fixed enum lifecycle
statuses and bounded structural timestamps are retained. Real lifecycle import,
provider mapping, schema-version changes and source admission require separate
contracts and evidence. Approval is an annotation, never proof of a completed
effect or an execution grant.

## Local I/O and review limits

The pure `import_trace(bytes, mapper=...)` library returns projection, report and
provenance without I/O. `read_trace` is an optional bounded local reader and
`validate_destination` checks an explicit new output path. Local paths reject
URIs, symlinks (including ancestors), collisions, existing outputs and special
source files. The CLI creates the output exclusively with owner-only permissions;
owned POSIX filesystem is assumed, and hostile same-UID ancestor replacement is
outside the security claim. Rejected content is absent from diagnostic codes.

Run the focused unittest suite for mapping, baseline parity, digest binding,
parser/privacy/path refusal and zero dispatch. These checks establish only their
finite synthetic controls. Provider spikes, ecosystem screening, real-source
rights/admission, independent reproduction, founder adoption and scientific
review remain separate pending work. This interface authorizes no agent/tool,
process, network, model, runtime execution or publication.
