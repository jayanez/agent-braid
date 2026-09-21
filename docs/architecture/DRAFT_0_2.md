# Evidence contracts — 0.2.0-draft

**Status:** experimental; no production runtime or automatic migration.

The versioned [AIM schema](../../schemas/0.2.0-draft/agent-interaction-metadata.schema.json)
and [certificate schema](../../schemas/0.2.0-draft/confluence-certificate.schema.json)
use JSON Schema 2020-12. All references are local; validators need no remote
schema download. Original 0.1 schemas and examples retain their original bytes.

## AIM envelope

`definition` identifies semantics and its digest; `instanceId` fixes an instance,
`inputDigest` binds its inputs and `attemptId` identifies an attempt. Dependencies
are other instance IDs; `readVersions` binds reads to resource versions.
`effects` preserves declared, inferred and observed records separately, with
explicit coverage status, domain and method. An empty list without complete,
justified coverage is not proof of purity. This envelope is descriptive metadata,
not an executable operation or authorization.

Each evidence record separates property, method, domain, assumptions, observation
and execution contract and the legacy `assuranceClass`. Declared, sampled and
formal evidence are not interchangeable. Even a complete coverage declaration
is a producer claim, not a conclusion independently established by this draft.

## Certificate evidence and checking

Certificates bind a finite integer-batch fixture and its identified operations.
They support `replay`, `exhaustive-finite`, and `proof-rule` evidence. Replay
requires at least two distinct complete schedules; exhaustive enumeration also
supports batches with only one admissible order. Both use terminal observation
claims only. Symbolic evidence requires a rule ID and bound proof artifact but
no enumerated schedules. The implemented checker does not evaluate proof languages
and returns `unverified` for these records, including a claimed level 5.

The verifier accepts an artifact map keyed by SHA-256 digest. Values are JSON
objects serialized by `json.dumps(sort_keys=True, separators=(',', ':'),
ensure_ascii=True, allow_nan=False)` and UTF-8 encoded. Only null, booleans,
strings, integers, lists and string-keyed dictionaries are accepted; floats,
non-finite numbers and duplicate input keys are rejected. This is a local
serialization contract, not a claim of general JSON canonicalization.

The fixture and every recorded outcome must exist under its correct digest.
The initial digest binds state and versions; operation digests bind full operation
records, not only names. The verifier checks identifiers, dependencies, model,
execution/observation contracts, assumptions, schedules and replayed outcomes.
For exhaustive evidence it reconstructs all admissible orders and requires exact
coverage. It recomputes the verdict and rejects a mismatched producer result.

Consumer reports are separate objects with status `verified`, `unverified`, or
`rejected`, a reason, and the checked claim when available. Verified means the
specific finite claim passed, never that the producer's entire assurance class
or a real-world execution is safe. Raw outcomes retain events even when terminal
projection excludes them. Blocked/error outcomes yield `inconclusive`.

## Migration from 0.1

Keep old records and their version. Do not copy a level into a verified status.
Assign stable instance/attempt IDs from real provenance, recover input and
definition artifacts, record known read versions and coverage gaps, and name
observation/execution contracts. Missing information stays unknown; do not invent
evidence. Certificates must be regenerated from supported immutable fixtures or
remain historical 0.1 records. A proof reference alone cannot promote a claim.

The bounded lab is one consumer of these contracts, not a general AIM runtime.
See [semantics](../theory/OPERATIONAL_SEMANTICS.md) and
[laboratory usage](../../research/lab/README.md).
