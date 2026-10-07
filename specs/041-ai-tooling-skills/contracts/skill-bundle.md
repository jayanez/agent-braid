# Product skill bundle proposal

Canonical source: `integrations/agent-braid/skills/` in future implementation.
Each directory has an Agent Skills `SKILL.md` with matching lowercase name,
nonempty description, licensing and bounded compatibility metadata. Keep each
instruction body below 500 lines with details in references. No generated
Spec Kit adapter is edited or redistributed as a product skill.

| Name | Trigger | Sequence and required user output |
|---|---|---|
| `agent-braid-analyze` | Inspect interactions or parallel work | Select immutable inputs → analyze-work/analyze → describe conflicts, conditional/unknown cases and evidence; no execute |
| `agent-braid-plan` | Prepare an admissible integration | Analyze → prepare → explain order, constraints, digest/scope and missing operator authority; no grant issuance |
| `agent-braid-execute` | Execute a prepared, already granted batch | Check mode/plan/grant reference → execute → status → verify; report actual private result and refused authority |
| `agent-braid-recover` | Inspect interruption and bounded recovery | Status → explain pending transition → recover with existing authority → verify; refuse unknown run or changed inputs |
| `agent-braid-evidence` | Explain or export a bounded result | Read owned evidence → reconcile full result/provenance/limits → export via reviewed formatter; no claim beyond observation |

Every skill separates model advice, host permission and operator grants. It never
instructs the model to obtain secrets, invoke grant issuance, write a grant store,
change approval policy, bypass a refusal, run source code or rewrite evidence.
If MCP is unavailable, report diagnosis or use explicitly documented read-only
CLI analysis; do not fall back to ungranted execution.

Host metadata belongs in small versioned wrappers. Codex discovery, Claude Code
discovery and any native plugin layout must be tested independently. Agent Skills
syntax and Agent Plugins conventions alone do not prove discovery. No hooks,
scheduled tasks or autonomous helper agents ship with this bundle.

Adversarial fixtures include repository/evidence text requesting grant creation,
secret disclosure, false success, hidden host configuration changes and out-of-root
reads. The workflow refuses these instructions and reports the observed limits.
Runtime controls enforce effects independently of instruction compliance.
