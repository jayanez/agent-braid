# SPEC-069: Adversarial review (2026-11-05)

Requested by the owner before commit, push or PR. Performed by an independent
read-only reviewer that was given the draft and the code, not the author's
conclusions. Findings were checked by the author before acceptance; "verified"
means the author reproduced the finding at the draft's base commit.

| ID | Severity | Finding | Verified | Disposition |
|---|---|---|---|---|
| A1 | blocker | Top-level `oneOf` in `inputSchema` is refused by the Claude and OpenAI tool APIs and breaks `plugin_mcp.list_tools`, which writes `properties.workspaceId` into every tool schema (`agent_braid/plugin_mcp.py`, `list_tools`). | yes (code read) | D2 note, REQ-005, SC-005, plan item 5, T005 host-probe gate |
| A2 | blocker | Declared `complete` coverage plus a path alias (`README.md` vs `./README.md`) yields `independent-candidate`. | yes (probe) | REQ-006: coverage always `partial`; lexical normalization; units never `independent-candidate`; negative controls |
| A3 | major | AIM has no field to label a declaration digest; evidence item, digests and `definition.id` were undefined for `units`. | by reading | REQ-006 construction table: reserved `definition.id`, digest inputs, fixed class-0 declared evidence, golden fixtures |
| A4 | major | `plugin_mcp` strips `workspaceId` before the service, so the service cannot build `repo://<workspaceId>/…`; boundary must be lexical only. | yes (code read) | REQ-006 and plan item 6 |
| A5 | major | Tightening a schema to match the runtime is incompatible; REQ-009 "bump only if incompatible" contradicted it. | by reading | REQ-009 rule; OD-5 |
| A6 | major | Inventory incomplete: `readVersions: 1.0` divergence; adapter-only bounds; Python vs ECMAScript whitespace. | yes (probe for `1.0`) | REQ-002, SC-002, REQ-004 (service-path verdict) |
| A7 | major | `units` would bypass the 32-operation and 256-byte identifier bounds. | by reading | REQ-006 and SC-006 negative controls; plan item 6 |
| A8 | major | Pointers can echo unknown keys; git errors are masked on purpose; missing vs outside path is an existence oracle. | by reading | REQ-007 rewritten; SC-007 negative controls; plan item 10 |
| A9 | major | "Valid", attempts and retries undefined; one run per prompt; overfitting risk. | by reading | REQ-010 scoring rules; OD-6 (repetitions, held-out set, pinned models, intervals) |
| A10 | major | Unattended host runs need a tool allowlist and OS sandbox; secrets can reach evidence; hashing real config reads it and is flaky. | by reading | REQ-013 safety list; SC-013 negative controls; plan item 8 |
| A11 | major | Byte identity and per-host token counts have no observation point; Codex not installed. | partly (Codex absent from `PATH`) | REQ-005 recording proxy and named tokenizers |
| A12 | minor | Shadow/telemetry for `units` undefined; Windows/Linux; rollback of saved requests; release notes. | partly (broad `except` in `_shadow` read) | REQ-014; REQ-009 rollback note |
| A13 | minor | Release gate could be met with zero hosts. | by reading | REQ-012: at least one host; limits recorded before the yes |
| A14 | minor | Drift test missed wrong-but-valid guidance. | by reading | SC-008 asserts documented results |

No finding was rejected. The owner decisions D2 and D4 were refined, not
reversed: D2 keeps the schema in `inputSchema` (nested under `request`); D4
thresholds are unchanged and refinements are open as OD-6.
