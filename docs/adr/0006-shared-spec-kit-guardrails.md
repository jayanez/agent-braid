# ADR 0006: Shared Spec Kit guardrails for Codex and Claude Code

## Status

Accepted for implementation by the founder's explicit integration request.
This is not a constitutional amendment or approval of future feature reviews.

## Context

We need traceable specifications without replacing the existing 25-article
Constitution, clause zero, semantics or scientific discipline. Contributors may
use either agent independently. Upstream command generation depends on the active
integration, and the default constitution command edits the memory document.

## Decision

Pin Spec Kit 1.0.7 at `fe1d00e3ccaf495880aaf90fb0e17679e82f065b`. Use its
official native skill adapters and Python helpers with a single override source.
Stage official init/install/use in temporary projects, refresh both selected
integrations, restore the selection, and explicitly supply overrides to adapters.
No global installations, auto-upgrades, presets, extensions or delivery workflows.

Keep the Constitution unchanged; generate only a byte-exact replica. Replace the
constitutional command with proposal-only behavior. Do not install constitution-sync.
The [guide](../development/SPEC_KIT.md) defines authority ordering, traceability,
fingerprints and maintenance. Terminal/CI gates check structure; agents interpret
requirements; humans judge normative/scientific questions and grant approvals.

## Alternatives

- Transforming the Constitution into the upstream template adds a second structural
  authority and unnecessary amendment risk.
- constitution-sync propagates edits into dependent documents; we need canonical
  text governed independently with a strictly derived replica.
- Separate agent policies drift and privilege one contributor environment.
- Default commands retain constitution-editing and violation-justification paths
  that conflict with the agreed controls.

## Consequences

The pinned adapter API needs explicit review on upgrades. Full command overrides
replace upstream workflow prose while preserving official rendering, native
formats and prerequisite helpers. We maintain and test those overrides. Hashes
detect change, not truth or approval. Negative/inconclusive research remains a
valid protocol outcome. No runtime, public contract or algorithm is changed.
