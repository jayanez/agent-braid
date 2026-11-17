# Contract `agent-braid-harness-mcp/v0.1`: read-only harness views over MCP

Status: **draft**, not implemented, not published. Publication follows SPEC-077
REQ-010 only.

## 1. Identity and host

- Result contract: `agent-braid-harness-mcp/v0.1`, carried as `harnessContract` in
  every result.
- Host: the native plugin MCP facade. Plugin envelope `agent-braid-plugin/v0.2`,
  unchanged; the four tools are plugin-owned and additive (OD-1).
- Not on the portable `agent-braid-tooling` server (its `v0.2` tool set is fixed).
- Available in every plugin capability mode, including `analysis-only`.

## 2. Invariants (MUST)

1. `executionAuthorization` is the JSON boolean `false` in every result, success or
   refusal. No field anywhere in a result may be `true` under that name.
2. No effects: a call creates, modifies or deletes no file, takes no lock, reads no
   clock, starts no subprocess, opens no socket and calls no host or model.
3. No native launch, laboratory attempt, containment probe, reservation, admission,
   grant, promotion, activation or registry write is reachable through these tools.
4. The tool set is exactly the four tools of section 3. `prepare`, `status`,
   `recover-inspect`, `inspect`, `validate` and `compare` are not exposed.
5. A result never contains a submitted argument value, an absolute host path, or
   file contents beyond the CLI view's own fields.
6. Host tool approval is not an operator grant and changes none of the above.

## 3. Tools

Every input schema is a flat JSON object with `additionalProperties: false`. The
description of each tool is the "Description" text below, verbatim, at most 2,048
UTF-8 bytes; it embeds the schema text so a host model sees it without reading a
resource.

Path rule (`path`): a workspace-relative POSIX path, 1 to 256 bytes, segments
separated by `/`, no leading `/`, no `.` or `..` segment, no empty segment, no `\`,
no NUL or control character. The JSON Schema states only the type and length; the
segment rules are runtime checks and refuse structurally with pointer `/path`.

### 3.1 `harness-capabilities`

- Input schema: `{"type":"object","properties":{},"additionalProperties":false}`
- Description: `Read-only. Lists the experimental harness CLI commands, their effects and the activation status. No arguments. Input schema: {"type":"object","properties":{},"additionalProperties":false}. Example: {}. Never launches, grants, promotes or activates; executionAuthorization is always false.`
- Result `view`: the CLI `harness capabilities` object.

### 3.2 `harness-registry-status`

- Input schema:
  `{"type":"object","properties":{"workspaceId":{"type":"string"},"path":{"type":"string","maxLength":256}},"required":["workspaceId","path"],"additionalProperties":false}`
- Description: `Read-only. Reports a SPEC-049 T013 profile registry's active, pending and audit state. Input schema: {"workspaceId": string (from the workspaces tool), "path": workspace-relative path to the registry JSON}. Example: {"workspaceId":"ws-1","path":"lab/profile-registry.json"}. Never promotes or activates; executionAuthorization is always false.`
- Result `view`: the CLI `harness registry-status <path>` object.

### 3.3 `harness-evaluation-summary`

- Input schema:
  `{"type":"object","properties":{"workspaceId":{"type":"string"},"path":{"type":"string","maxLength":256},"sha256":{"type":"string","pattern":"^[0-9a-f]{64}$"}},"required":["workspaceId","path"],"additionalProperties":false}`
- Description: `Read-only. Summarizes a SPEC-049 T003 evaluation report per stratum. Input schema: {"workspaceId": string, "path": workspace-relative path to the report JSON, "sha256": optional 64 lowercase hex digest you were given from outside the report}. Example: {"workspaceId":"ws-1","path":"lab/evaluation-report.json"}. A matched sha256 binds bytes, not authenticity. executionAuthorization is always false.`
- Result `view`: the CLI `harness evaluation-summary <path> [--sha256 H]` object.

### 3.4 `harness-evidence`

- Input schema:
  `{"type":"object","properties":{"workspaceId":{"type":"string"},"path":{"type":"string","maxLength":256}},"required":["workspaceId","path"],"additionalProperties":false}`
- Description: `Read-only. Inventories a spec directory's evidence files against its tasks.md. Input schema: {"workspaceId": string, "path": workspace-relative spec directory}. Example: {"workspaceId":"ws-1","path":"specs/049-harness-evaluation-learning"}. Hashes bind bytes; contents and checkboxes are not verified. executionAuthorization is always false.`
- Result `view`: the CLI `harness evidence <path>` object.

## 4. Path resolution

The path is resolved under the registered workspace's source root by opening each
segment relative to the previous directory descriptor with `O_NOFOLLOW`
(directories with `O_DIRECTORY`). The final component must be a regular file (or a
directory for `harness-evidence`). A missing component, a symbolic link at any
segment, a special file, or a resolution outside the root all return the same
refusal: reason `input-unreadable`, pointer `/path`. The registered root itself is
taken from the plugin registry, never from arguments.

## 5. Results

Success:

```json
{"status": "ok", "executionAuthorization": false,
 "harnessContract": "agent-braid-harness-mcp/v0.1",
 "schemaVersion": "agent-braid-plugin/v0.2", "workspaceId": "ws-1",
 "tool": "harness-evidence", "view": { "...": "CLI view object" }}
```

`view` equals the CLI's stdout object for the same input bytes minus its `status`
and `executionAuthorization` keys (SPEC-077 REQ-006). `workspaceId` is `null` for
`harness-capabilities`.

Bound: the serialized result is at most 65,536 bytes. A larger result is refused
with reason `output-too-large` and `observed` counts (`bytes`, and `files` or
`decisions` where applicable). Results are never truncated. Inputs keep the CLI
bounds: 1,048,576-byte records, 256 evidence files, 1,024 walked entries, depth 4.

## 6. Refusals

```json
{"status": "refused", "executionAuthorization": false,
 "harnessContract": "agent-braid-harness-mcp/v0.1",
 "tool": "harness-evaluation-summary", "class": "structural",
 "reason": "invalid-argument", "pointer": "/sha256",
 "expected": "64 lowercase hexadecimal characters"}
```

- `class` is `structural` (arguments do not match the schema) or `semantic` (the
  input file or its content is refused).
- `pointer` is an RFC 6901 JSON Pointer into the call arguments: the failing
  argument for a structural refusal; the argument that carried the input (`/path`,
  `/sha256`) for a semantic one; `""` when no argument applies.
- Structural reasons: `invalid-argument`, `unknown-argument`, `missing-argument`.
  `expected` states the expected form; an unknown key appears only as
  `<key:digest8>` (first 8 hex of its SHA-256).
- Semantic reasons: exactly the CLI's fixed codes (for example `input-unreadable`,
  `input-too-large`, `invalid-json`, `non-canonical`, `record-drift`,
  `invalid-evaluation`, `invalid-tasks`, `too-many-entries`, `too-deep`) plus
  `output-too-large` and `unknown-workspace`.
- Refusals never echo values, never reveal whether a host path exists, and are at
  most 1,024 characters.

## 7. Versioning

Any change to tool names, input schemas, descriptions, `view` shape or refusal
codes is a new `agent-braid-harness-mcp` version with its own review. Adding a
harness tool with effects is out of scope for this contract family; it would need a
separate execution contract under the SPEC-065 operator model.
