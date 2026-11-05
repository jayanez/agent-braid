# Activity viewer UI, security and privacy contract (draft)

This is the "Embedded visual interaction" contract that SPEC-039
[program](../../039-ai-tooling-program/program.md) requires before any embedded
or host-native view. It binds VIS.1. Later VIS tracks start from it but each needs
its own boundary review where it widens a route, an origin or a credential (see
[Later surfaces](#later-surfaces)).

## Authority and effect

- The viewer is read-only. No route, message, button or keyboard action executes,
  schedules, retries, cancels, grants, writes to a repository, registry, run
  directory or host configuration, or calls an Agent Braid command with effects.
- The viewer never takes part in a host decision. Hook routes accept only
  observational events and every response to a hook route has an empty body, so a
  host cannot read an approval, a denial, a rewritten input or a continuation
  instruction from it. Decision events (`PreToolUse`, `PermissionRequest`,
  `UserPromptSubmit`, `Stop` and any event not listed below) are refused.
- Every event carries `executionAuthorization: false`. A rendered class, colour or
  counter is never an authorization, a guarantee, a safety ordering or permission
  to interleave work.

## Network boundary

- Bind to `127.0.0.1` or `::1` only, on an OS-assigned port unless the user passes
  `--port`. No `0.0.0.0`, no remote listener, no outbound connection. Access
  logging is disabled.
- Credentials (each at least 128 bits from `secrets`, valid for one server
  session, with separate rights):
  - **Open code.** Printed once at start as `http://127.0.0.1:<port>/open?code=<c>`.
    The first valid request exchanges it for an `HttpOnly; SameSite=Strict; Path=/`
    session cookie and answers `303` to `/`; the code is then invalid. The cookie is
    named `braid_view_<port>` (the viewer's own port), because browsers share cookies
    across loopback ports and two viewers must not overwrite each other's session.
    The cookie grants read routes only.
  - **Open code on demand** (amendment 2026-11-05, VIS.1d T067). The owner can ask a
    running viewer for a new open code with `agent-braid view open`, so another browser
    can open it without a restart. Such a code is single use and expires 120 seconds
    after it is issued. At most 4 issued codes are pending at once; the oldest is
    dropped beyond that. Each exchange of any open code creates its own read cookie
    value, so a browser that opened the viewer earlier stays connected. At most 8 read
    cookie values are valid at once; the oldest is dropped beyond that. The read cookie
    never mints a code, and the page has no control that does.
  - **Owner token** (amendment 2026-11-05, VIS.1d T067). New at every start and written
    to `<runtime dir>/view-owner-<port>`, created exclusively with mode 0600. A file left
    by a viewer that did not stop cleanly is replaced only when it is a regular file
    owned by the user. The file is removed when the viewer stops. It is sent only by
    `agent-braid view open` as `Authorization: Bearer <token>` on the loopback port. It
    grants only the open-code route: it cannot read and cannot ingest. It is never
    printed, never put in a URL and never written into host configuration.
  - **Ingest token.** Kept in a file with owner-only permissions in a per-user
    runtime directory. At start an existing file is reused when it is a regular file
    (no symbolic link, one link) owned by the user, mode 0600, holding one well-formed
    token; otherwise, or with `serve --rotate-token`, a new token is written to a file
    created exclusively and moved into place. The file is kept when the viewer stops,
    so hosts that read it once keep working across restarts (amendment 2026-11-04 in
    the spec). The start text says whether it was reused or is new. It is sent by host exporters as `Authorization: Bearer <token>`. It grants ingest
    routes only and cannot read. It is never printed, never put in a URL and never
    written into host configuration; printed configuration reads it from the file.
    The printed Claude Code hooks (amendment 2026-11-04b) are commands that read the
    file at every call and pass the token to the loopback request only inside the
    hook process: never in the settings, in argv, in the environment or in output,
    and never through a proxy. The hook command always exits 0 and prints nothing.
- Allowed `Host` values are exactly `127.0.0.1:<port>`, `[::1]:<port>` and
  `localhost:<port>`. A request whose `Origin`, when present, is not the same
  loopback origin, or whose `Sec-Fetch-Site` is `cross-site`, is refused. OTLP and
  hook posts from host processes carry no `Origin` and must carry the ingest token.
- Response headers on every response: `Content-Security-Policy: default-src 'self';
  script-src 'self' 'sha256-<import map>'; style-src 'self'; img-src 'self' data:;
  connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self';
  require-trusted-types-for 'script'`, `X-Content-Type-Options: nosniff`,
  `Referrer-Policy: no-referrer`, `Cache-Control: no-store`. The `<import map>`
  hash is the SHA-256 of the single inline import map in `index.html`. A `<meta>`
  copy of the policy, if present for file-based viewing, omits `frame-ancestors`,
  which browsers ignore in meta.
- Bodies: OTLP at most 1 MiB, hooks at most 256 KiB, a `Content-Length` is
  required, and only the identity content encoding is accepted. JSON parsing
  refuses duplicate members, non-finite numbers (including overflowing literals
  such as `1e400`) and depth beyond 64, checked without recursion.
- At most 8 Server-Sent Events subscribers (each receives a heartbeat every 15
  seconds and is dropped when it cannot be written), at most 32 concurrent
  connections and a 10-second socket timeout. The timeout also bounds the whole request: reading
  the request line, headers and body stops at one 10-second deadline, so a client that sends one
  byte at a time does not keep a connection slot.

### Refusal statuses

| Condition | Status | State change |
|---|---|---|
| Unknown path, missing or wrong credential, reused open code | 404 | none |
| Read credential on an ingest route or ingest credential on a read route | 404 | none |
| Any credential other than the owner token on the open-code route | 404 | none |
| A body on the open-code route | 413 | none |
| Method not allowed on a known path | 405 | none |
| Foreign `Host`, foreign `Origin` or cross-site `Sec-Fetch-Site` | 403 | none |
| Decision hook event | 403, empty body | none |
| Malformed JSON, duplicate members, non-finite number, excessive depth, schema violation | 400 | none |
| Missing `Content-Length` | 411 | none |
| Body over its limit | 413 | none |
| Content type other than `application/json` or a content encoding other than identity (ingest) | 415 | none |
| Ninth subscriber or connection limit reached | 503 | none |
| Per-kind cap reached on ingest | 503 | input beyond the cap is not stored; one `stream-truncated` gap |

A wrong credential returns 404 so the route space is not revealed. Every response
on a hook route, including a refusal, has an empty body. Host verification T030
records whether the installed Claude Code treats these responses as non-blocking.

## Routes

| Method | Route | Credential | Effect |
|---|---|---|---|
| GET | `/open?code=<c>` | open code | sets the read cookie, `303` to `/` |
| GET | `/` and `/web/<file>` | read cookie | static bundle; only the first-party files the viewer lists (`BUNDLE_FILES`, pinned to the source bundle by a test); the vendored files by the vendor manifest below |
| GET | `/events` | read cookie | SSE, resumes from `Last-Event-ID` |
| GET | `/snapshot` | read cookie | current viewer model and the dropped-attribute names inventory |
| GET | `/frame.svg`, `/frame.txt` | read cookie | pure frame rendering |
| POST | `/v1/logs`, `/v1/metrics` | ingest token | OTLP HTTP/JSON ingest, append to memory |
| POST | `/hook/claude` | ingest token | observational Claude Code HTTP hook ingest, empty response body |
| POST | `/v1/open-code` | owner token | issues one open code (single use, 120 s) and answers `{"url", "ttlSeconds"}`; no body accepted |

Any other path returns 404 without state change. VIS.1 has no route that accepts
loom lines from another process and no Codex `notify` or hook route (VIS.3).

## Verification status

`source.verification` is assigned by the viewer when it ingests an event and is
never taken from a file or a post:

- `rehashed`: an adapter read the artifact under a root the user named and the
  `evidenceRef` hash was computed by this viewer session;
- `derived`: the viewer derived the event from rehashed events (a grant expiry);
- `unverified`: every replayed event and every host-reported event (OTLP, hooks).

Unverified crossings and gate results carry a distinct unverified marker in every
view and are never counted as verified facts.

## Data minimization

Canonical allowlist (the only attributes whose values are kept), applied at every
OTLP level (resource, scope, log record, metric data point and exemplar):

- Claude Code OpenTelemetry: `model`, `cost_usd`, `input_tokens`, `output_tokens`,
  `cache_read_tokens`, `cache_creation_tokens`, `duration_ms`, `session.id`,
  `prompt.id` (salted, used only to group a turn), `tool_name`, `decision`, `query_source`.
  Host verification T030 found no `agent_id` or `parent_agent_id` attribute in Claude Code
  OpenTelemetry, so subagent attribution comes from the hook `agent_id` below.
- Codex OpenTelemetry: the per-turn token usage attributes (input, cached input,
  output, reasoning output, total), `model`, conversation and thread identifiers
  (salted). Exact names are pinned by host verification T031; until then unpinned
  names produce `shape-unpinned`.
- Claude Code hooks: `hook_event_name` (observational events `SessionStart`,
  `SessionEnd`, `SubagentStart`, `SubagentStop`, `PostToolUse` only), `agent_id`,
  `agent_type`, `session_id`, `tool_name`, `tool_use_id` (identifiers salted), and
  `duration_ms` on `PostToolUse` only (T062, 2026-11-04: the T030 receipt names it and the
  owner accepted that evidence when closing T053; only a JSON integer from 0 to 86,400,000 is
  kept, as the in-memory `toolDurationMs`, and any other shape is dropped with one
  `shape-unpinned` gap; on any other event the name is inventoried as dropped). Pinned from the
  T030 receipt. An HTTP `SessionStart` was not delivered under `claude -p`, so nothing
  depends on it: a strand opens on the first event that mentions it. A strand that was
  closed stays closed: an event that would continue it adds one `shape-unpinned` gap naming the
  strand instead of activity, and a repeated `SessionEnd` or `SubagentStop` adds nothing. At most
  1,024 strand identifiers are tracked; beyond that no new strand opens and one
  `stream-truncated` gap says so. Every other payload
  name (for example `tool_input.*`, `tool_response.*`, `last_assistant_message`, `cwd`,
  `transcript_path`, `agent_transcript_path`, `scratchpad_dir`, prompt fields) is dropped and
  only its name enters the dropped-attribute inventory.
- Host stream events (`claude -p` stream-json, `codex exec --json`): event type,
  usage counts, model and identifiers (salted); every message, prompt, tool input
  and tool output field is dropped before any other processing.

Rules:

- Never retained: prompt or message text, OTLP log bodies, tool input, tool output,
  file content, `transcript_path`, user e-mail or account identifiers,
  organisation identifiers, terminal type, absolute timestamps.
- Kept string values are at most 256 characters and follow the free-text rule: no
  C0 or C1 control character, no DEL and no bidirectional override.
- Identifiers are replaced by `HMAC-SHA256(sessionSalt, value)` truncated to 16 hex
  characters. The salt lives in memory for one server session.
- Names of dropped attributes (never their values) are kept in an in-memory
  inventory of at most 256 names of at most 64 characters, shown in `/snapshot`
  for host verification and never exported.
- Time is `relMs` from a monotonic clock started with the server.
- `evidenceRef.path` is relative to the root the user named, with no `..` segment
  and no drive prefix; absolute paths are kept only in memory for the evidence
  panel. Default export also replaces absolute-path-like values in every other
  string field with a fixed marker.

What the minimization does not cover: an exporter or a hook still sends its full
payload to the loopback port before the viewer drops fields. Whatever process
listens on that port receives it; if the viewer is not running and another process
holds the port, hosts send their telemetry to that process. Users configure
exporters only while the viewer runs, and `view env` says so.

### Deviations from the never-collect list

The SPEC-057 never-collect list and the [telemetry policy](../../../docs/tooling/TELEMETRY.md)
govern telemetry about Agent Braid commands. The viewer writes no telemetry, but
it holds the following categories outside that policy, under owner decision D4:

| Category | Held in | Retention | Default export | With `--record-effort` / `--include-effort` | Why |
|---|---|---|---|---|---|
| Token counts and cost | process memory | server session | omitted | recorded exactly / exported per arm, strand, host and model | effort view and comparison |
| Exact durations | process memory | server session | omitted | recorded exactly / exported as buckets | effort view; buckets limit precision in packs |
| Exact model identifier | process memory | server session | omitted | recorded / exported | comparisons are meaningless across models |
| Salted identifiers | memory, recordings | server session or recording file | kept (salted, unlinkable across sessions) | same | strand identity |
| Relative artifact paths and SHA-256 hashes | memory, recordings | server session or recording file | kept | same | Article 14 evidence inspection |
| Sub-day relative time (`relMs`) | memory, recordings | server session or recording file | kept | same | ordering and playback |

### Contract v0.2 amendment (2026-11-04, T052)

`agent-braid-loom/v0.2` ([schema](loom-event.v0.2.schema.json)) passed the G3 privacy
review recorded in
[contract-v0.2-privacy-review.md](../vis1c/contract-v0.2-privacy-review.md). The v0.1
[schema](loom-event.schema.json) is frozen and stays valid input: the viewer and
`view validate` accept both versions, `view validate` reports how many events of each it
read, and this package's adapters emit v0.1 except where they set a v0.2 member (T061, T062). v0.2 adds three optional members to
`strand.update` and nothing else; none carries content, a path or an absolute time:

- `toolDurationMs`: an integer from 0 to 86,400,000 that a host reported for one tool
  call. It is never derived from the interval between events (that interval is labelled
  as such, never as a duration). Under owner decision OD-V4 (a) it is held in process
  memory only: a replayed stream loses it on load, and no recording or export, with or
  without `--record-effort` or `--include-effort`, carries it. Wider retention needs a new
  owner decision. No host payload name is added to the allowlist by this amendment; a
  hook or OTLP source is pinned only through the task that implements it (T062), from a
  probe receipt. T062 pinned the hook `PostToolUse.duration_ms` on 2026-11-04 (see the
  Claude Code hooks allowlist above); the adapters add `toolDurationMs` in v0.2 events only.
- `waitingOn`: one salted strand identifier (the identifier class above), present only
  when `state` is `waiting` and always together with `waitingBasis`. It is never parsed
  from host text. A strand never waits on itself; an adapter drops a target that is not a
  strand of the same session and adds one `shape-unpinned` gap.
- `waitingBasis`: `declared` (ordered by a plan, scheduler or analysis) or `observed` (a
  host reported the wait). A declared wait is never shown as an observed one.

The snapshot `axis` may gain `nowMs` (the viewer's monotonic clock at snapshot time,
same basis as `relMs`, never earlier than the last event) and `live` (`false` for a
replay, where `nowMs` equals the last event time). They describe the snapshot, are not
events and are never recorded. Since T060 (2026-11-04) `/snapshot` always carries both: `live` is
true while `view serve` runs without `--replay`, and `nowMs` is then the server clock, clamped
to the last event time. The `collision.observed` kind of the draft is **not** in
v0.2: its per-adapter observation boundary must be written first (T063).

| Category | Held in | Retention | Default export | With `--record-effort` / `--include-effort` | Why |
|---|---|---|---|---|---|
| Tool call duration (`toolDurationMs`, v0.2) | process memory | server session | omitted | omitted (OD-V4 (a)) | how long a tool call took, live only |

Recordings and exports are private files on the user's machine. Sharing one is
the user's decision; presenting a pack as evidence of Agent Braid's effect is a
public claim under [GOVERNANCE.md](../../../GOVERNANCE.md).

## Persistence

- `serve` writes nothing unless the user passes `--record FILE`; effort events are
  recorded only with `--record-effort`. `export --to PATH` writes only to the named
  destination. Both use SPEC-043 destination rules (absolute path, new, private
  user-owned parent, outside repositories, no symlink) and create files
  exclusively without following a symbolic link (`O_CREAT | O_EXCL |
  O_NOFOLLOW`, mode 0600); an export directory is created with mode 0700 and
  written relative to its directory descriptor.
- `--watch` reads only known artifact names, opens regular files without
  following symbolic links and refuses any file whose resolved path leaves the
  named root.
- The viewer never reads or writes the SPEC-047 telemetry store.

## Rendering

- Static bundle with vendored Three.js (ADR 0033) and a hash manifest; first-party
  files contain no remote URL, no `eval`, no `Function` constructor and no inline
  script other than the hashed import map; no import, `src`, `href` or fetch in
  first-party files or the import map targets a remote origin. Vendored files are
  checked by manifest hash only; runtime remote loads are also blocked by the CSP.
- `/web/vendor/<path>` serves a nested vendored file only when `web/vendor/manifest.json` lists it and its SHA-256 matches at request time, and refuses everything else (unlisted, mismatched, symbolic link, traversal) with the same headers; owner approval 2026-11-02 (T025): "Sí, solo lo del manifest (Recommended)".
- Text from events is inserted as text nodes, never as HTML; the trusted-types
  directive makes the browser refuse HTML sinks.
- Exported HTML and SVG escape every text and attribute value; exported
  `index.html` carries `<meta http-equiv="Content-Security-Policy"
  content="default-src 'none'; img-src 'self' data:; style-src 'self'">`;
  `summary.md` escapes Markdown and contains no link or image syntax.
- Terminal frames escape C0 and C1 control characters, DEL and bidirectional
  overrides.
- A table view presents the same facts without WebGL; colour is never the only
  carrier of a classification or class (shape and label also differ).

## Later surfaces

VIS.2 (Claude Code mod), VIS.3 (Codex hooks and `notify`, MCP App, terminal UI)
and VIS.4 keep the authority, minimization and rendering rules above. They do not
inherit a route, origin or credential VIS.1 lacks:

- A mod handler observes only: it passes every event on unchanged and returns no
  decision. Any route that accepts loom lines from a mod is specified, with its
  own credential and verification status (`unverified`), in SPEC-062.
- An MCP App runs in a host iframe with a foreign `Origin`, which this contract
  refuses, and inlining Three.js leaves the ADR 0033 boundary. SPEC-063 needs its
  own boundary decision (and an ADR 0033 amendment if it inlines vendored code).
- A Codex `notify` or hook shim must exit 0 with empty output on every path.
- Opening the viewer in an agent-driven browser pane can bring page text (labels,
  effort) into a model's context; host verification T032 is run with the owner
  opening the page, and documentation states this exposure.
