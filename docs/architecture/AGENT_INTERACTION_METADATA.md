# Agent Interaction Metadata (AIM) — Draft 0

AIM is a proposed portable vocabulary for describing the effects and algebraic properties of agent operations. It is a research draft, not a standard.

This page preserves the 0.1 vocabulary. See [draft 0.2 and migration](DRAFT_0_2.md)
for versioned instance identities, evidence dimensions and coverage. The original
schema remains unchanged and does not establish complete effect coverage.

## Design goals

- protocol- and model-agnostic;
- useful with partial metadata;
- explicit about provenance and assurance;
- able to name conditions rather than flattening them into booleans;
- extensible without changing the core semantics;
- safe by default when effects are unknown.

## Minimal operation

```json
{
  "aimVersion": "0.1.0-draft",
  "operation": "repository.update_file",
  "effects": [
    {
      "kind": "read",
      "resource": "repo://jayanez/agent-braid/README.md"
    },
    {
      "kind": "write",
      "resource": "repo://jayanez/agent-braid/README.md"
    }
  ],
  "properties": {
    "determinism": "conditional",
    "idempotence": "conditional",
    "reversibility": "compensatable"
  },
  "evidence": {
    "source": "declared",
    "assuranceLevel": 0
  }
}
```

## Resource identity

Resource URIs are semantic identifiers, not necessarily fetchable URLs. Adapters define schemes and aliasing rules. Range fragments may refine a resource but cannot prove independence by themselves.

## Property values

Properties should prefer four-valued classifications where appropriate:

- `yes`
- `no`
- `conditional`
- `unknown`

Conditions reference named predicates with versioned definitions. Free-text conditions may explain a rule but are not machine-enforceable.

## Provenance

An effect or property may be:

- declared by the provider;
- inferred statically;
- observed dynamically;
- established empirically;
- derived by a proof rule;
- formally proved.

Conflicting evidence is retained. Consumers choose policy; AIM does not silently promote the strongest-looking claim.

## Interactions

Pair or higher-order interaction records may state a classification, conditions, observation boundary, evidence, and counterexample reference. A plain `commutative: true` field is intentionally insufficient for strong claims.

See [the JSON schema](../../schemas/agent-interaction-metadata.schema.json) and [the example](../../examples/aim/file-edits.json).
