# Activity viewer UI, security and privacy contract (draft)

This is the "Embedded visual interaction" contract that SPEC-039
[program](../../039-ai-tooling-program/program.md) requires before any embedded
or host-native view. It binds VIS.1 and every later VIS surface.

## Authority and effect

- The viewer is read-only. No route, message, button or keyboard action executes,
  schedules, retries, cancels, grants, writes to a repository, registry, run
  directory or host configuration, or calls an Agent Braid command with effects.
- Every event carries `executionAuthorization: false`. A rendered class, colour or
  counter is never an authorization, a guarantee or a safety ordering.

## Network boundary

- Bind to `127.0.0.1` or `::1` only, on an OS-assigned port unless the user passes
  `--port`. No `0.0.0.0`, no remote listener, no outbound connection.
- A random per-session token (at least 128 bits from `secrets`) prefixes every
  route: `/t/<token>/...`. It is printed once at start and never persisted.
- Refuse a request whose `Host` is not a loopback name with the bound port, or
  whose `Origin`, when present, is not the same loopback origin. OTLP and hook
  posts from host processes carry no `Origin` and must carry the token.
- Response headers on every response: `Content-Security-Policy: default-src 'self';
  script-src 'self' 'sha256-<import map>'; style-src 'self'; img-src 'self' data:;
  connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'`,
  `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`,
  `Cache-Control: no-store`. The `<import map>` hash is the SHA-256 of the single
  inline import map in `index.html`. A `<meta>` copy of the policy, if present for
  file-based viewing, omits `frame-ancestors`, which browsers ignore in meta.
- Bodies: OTLP at most 1 MiB, hooks and notify at most 256 KiB, loom POST bodies at
  most 1 MiB with lines of at most 16 KiB. JSON parsing refuses duplicate members,
  non-finite numbers and depth beyond 64.
- At most 8 Server-Sent Events subscribers.

### Refusal statuses

| Condition | Status | State change |
|---|---|---|
| Unknown path or wrong token | 404 | none |
| Method not allowed on a known path | 405 | none |
| Foreign `Host` or `Origin` | 403 | none |
| Malformed JSON, duplicate members, non-finite number, schema violation | 400 | none |
| Body over its limit | 413 | none |
| Content type other than `application/json` (ingest) | 415 | none |
| Ninth subscriber | 503 | none |
| Per-kind cap reached on ingest | 503 | input beyond the cap is not stored; one `stream-truncated` gap |

A wrong token returns 404 so the route space is not revealed.

## Routes

| Method | Route (under `/t/<token>`) | Effect |
|---|---|---|
| GET | `/` and `/web/*` | static bundle |
| GET | `/events` | SSE, resumes from `Last-Event-ID` |
| GET | `/snapshot` | current viewer model and the dropped-attribute names inventory |
| GET | `/frame.svg`, `/frame.txt` | pure frame rendering |
| POST | `/v1/logs`, `/v1/metrics` | OTLP HTTP/JSON ingest, append to memory |
| POST | `/hook/claude` | Claude Code HTTP hook ingest |
| POST | `/notify/codex`, `/hook/codex` | Codex notify or hook shim ingest |
| POST | `/loom` | validated loom lines from a local companion |

Any other path returns 404 without state change.

## Data minimization

Canonical allowlist (the only attributes whose values are kept):

- Claude Code OpenTelemetry: `model`, `cost_usd`, `input_tokens`, `output_tokens`,
  `cache_read_tokens`, `cache_creation_tokens`, `duration_ms`, `agent_id`,
  `parent_agent_id`, `session.id`, `prompt.id` (salted, used only to group a turn),
  `tool_name`, `decision`, `query_source`.
- Codex OpenTelemetry: the per-turn token usage attributes (input, cached input,
  output, reasoning output, total), `model`, conversation and thread identifiers
  (salted). Exact names are pinned by host verification T031; until then unpinned
  names produce `shape-unpinned`.
- Hooks and notify: event name, `agent_id`, `agent_type`, `session_id`, `tool_name`,
  `tool_use_id` (salted identifiers only); Codex `notify` type and turn identifier.

Rules:

- Never retained: prompt or message text, tool input, tool output, file content,
  user e-mail or account identifiers, organisation identifiers, terminal type,
  absolute timestamps.
- Identifiers are replaced by `HMAC-SHA256(sessionSalt, value)` truncated to 16 hex
  characters. The salt lives in memory for one server session.
- Names of dropped attributes (never their values) are kept in an in-memory
  inventory of at most 256 names of at most 64 characters, shown in `/snapshot`
  for host verification and never exported.
- Time is `relMs` from a monotonic clock started with the server.
- `evidenceRef.path` is relative to the root the user named, with no `..` segment
  and no drive prefix; absolute paths are kept only in memory for the evidence
  panel and removed by default export.

## Persistence

- `serve` writes nothing unless the user passes `--record FILE`; effort events are
  recorded only with `--record-effort`. `export --to PATH` writes only to the named
  destination. Both use SPEC-043 destination rules: absolute path, new, private
  user-owned parent, outside repositories, no symlink.
- The viewer never reads or writes the SPEC-047 telemetry store.

## Rendering

- Static bundle with vendored Three.js (ADR 0033) and a hash manifest; first-party
  files contain no remote URL, no `eval`, no `Function` constructor and no inline
  script other than the hashed import map; no import, `src`, `href` or fetch in
  first-party files or the import map targets a remote origin. Vendored files are
  checked by manifest hash only; runtime remote loads are also blocked by the CSP.
- Text from events is inserted as text nodes, never as HTML.
- Terminal frames escape control characters as in SPEC-043.
- A table view presents the same facts without WebGL; colour is never the only
  carrier of a classification or class (shape and label also differ).

## Later surfaces

VIS.2 (Claude Code mod), VIS.3 (Codex MCP App, terminal UI) and VIS.4 inherit
this contract. An MCP App declares `connectDomains` limited to the loopback origin
and no `resourceDomains`; a mod reads `/frame.svg` or frame buffers only.
