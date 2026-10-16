# Portable product skills

The canonical bundle contains five skills: `agent-braid-analyze`,
`agent-braid-plan`, `agent-braid-execute`, `agent-braid-recover` and
`agent-braid-evidence`. Their shared instructions live outside generated Spec Kit
adapters and are packaged as resources. The bundle loader reports exact names,
descriptions, licenses, versions and hashes; it does not prove host discovery.

Analysis is advisory. Planning preserves the exact digest, ordering, constraints
and missing permission. Execution and recovery consume existing independently
issued operator grants, then inspect status and verify the actual result.
Evidence guidance retains provenance, unknowns and observation limits.
No skill issues grants, installs hooks or changes approval policy. Host tool
permission never substitutes for a core grant.

Use the [installation workflow](INSTALL.md) for explicit receipt-owned changes.
Missing MCP/skills/SDK capabilities require actionable diagnostics; only a
documented read-only fallback is allowed. Repository text and evidence remain
untrusted data, including instructions to expose secrets or claim false success.

See the [SPEC-041 engineering quickstart](../../specs/041-ai-tooling-skills/quickstart.md)
for the fixed synthetic control capture, and its
[implementation map](../../specs/041-ai-tooling-skills/implementation-status.md)
for all eight requirements and coordination with FC.1/M4.5. Actual native loading
and model compliance must be observed separately in both supported hosts.
