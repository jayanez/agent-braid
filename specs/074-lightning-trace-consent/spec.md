# SPEC-074: Lightning trace consent

**Milestone:** BL.4 — Lightning trace consent (GitHub milestone created by the
reviewed tracking reconciliation after merge).

**Status:** draft. OD-1 to OD-3 are decided (T001 owner review recorded
2026-11-13, [review](reviews/owner-t001-20261113.md)); `human_review` is
pending. ADR 0041 (content-bearing traces) was accepted by the owner on
2026-11-08 and applies when this specification is delivered. No content is
collected until the owner records consent.

## Purpose and scope

Braid Lightning optimizes text from rollouts. Until now Agent Braid telemetry is
content-free (ADR 0025, `docs/tooling/TELEMETRY.md`) and the Lightning store
refuses content fields while `traces.contentConsent` is `none` (SPEC-070
REQ-006). This specification defines when and how content-bearing traces may
exist: an explicit consent level, a redaction pipeline applied before any byte
is stored, bounded retention with purge, and an adapter that turns the sources
into upstream-shaped triplets and messages. It is engineering, not a research
protocol.

In scope:

- the consent contract: `traces.contentConsent` in `lightning.json`
  (`none` | `redacted`), changed only through `agent-braid lightning init`
  preview and apply with digest (`plugin setup` only sets `lightning`
  `off` | `lab`);
- `agent_braid/lightning_redact.py`: redaction of secrets, tokens, emails, home
  paths and API-key patterns, reusing the `scripts/spec069_native_runs.py`
  pattern set and literal-value scan;
- retention (default 30 days, maximum 90) and content purge, extending the
  BL.0 (SPEC-070) `agent-braid lightning purge`;
- `agent_braid/lightning_adapter.py`, porting agent-lightning v0.x
  `TracerTraceToTriplet` and `TraceToMessages`;
- adapter inputs: Lightning rollout records, host transcripts (through
  `trace_adapter` and the Claude and Codex observers), the Loom stream, and
  System One shadow episodes (read-only);
- an extension of the `traces` section of
  `schemas/0.3.0-experimental/lightning-config.schema.json` (no separate
  consent schema);
- [privacy-review.md](privacy-review.md).

Exclusions:

- Any consent level that stores unredacted content; there is no `raw` level.
- Writing to System One, its shadow store or its decisions (ADR 0034).
- Sending traces off the machine; dataset export (SPEC-075); training (SPEC-076).
- Changes to existing content-free telemetry.

## Authorities

Constitution clause zero and Articles 13, 14, 16, 19, 20 and 23;
[GOVERNANCE.md](../../GOVERNANCE.md);
[claim discipline](../../docs/theory/CLAIM_DISCIPLINE.md);
[ADR 0025](../../docs/adr/0025-local-technical-telemetry.md) (local technical
telemetry), [ADR 0034](../../docs/adr/0034-system-one-shadow-advisory-boundary.md)
(System One advisory boundary), [ADR 0041](../../docs/adr/0041-braid-lightning-content-traces.md) (content-bearing traces, accepted 2026-11-08);
[real-use evidence](../../docs/development/REAL_USE_EVIDENCE.md). Precedents:
[SPEC-066](../066-system-one-shadow/spec.md) (validated episodes, 30-day
retention, purge) and [SPEC-069](../069-aim-request-authoring/spec.md)
(redaction and secret scan). Program:
[SPEC-070 program](../070-braid-lightning-foundations/program.md) and
[configuration contract](../070-braid-lightning-foundations/contracts/lightning-config.md).

## Clarifications

Design decisions recorded for owner review:

- **C1 — Two levels only.** `none` (default) keeps every record content-free;
  `redacted` allows content after redaction. Consent is per configuration, and
  changing it requires a new preview digest.
- **C2 — Redact on ingest.** Redaction runs before a record reaches the store or
  an adapter output; a record whose post-redaction scan still finds a secret is
  refused, not stored.
- **C3 — Fail closed.** An unreadable or invalid configuration means `none`.
- **C4 — Read-only sources.** Host transcripts, Loom and System One episodes are
  read; their files are never modified or deleted by this feature.
- **C5 — Shape.** Triplets are `{prompt, response, reward, metadata}` and
  messages are role/content lists, matching upstream shapes so SPEC-075 can
  export them.

Owner decisions (decided 2026-11-13, T001):

- **OD-1 — Host transcripts as a source: yes, opt-in.** `host-transcript` is an
  allowed value of `traces.sources` in the first release; the default stays
  `["rollout"]`, so transcripts are read only after the owner lists the source
  through the previewed `lightning init`.
- **OD-2 — Emails: masked with a per-run salted hash.** Placeholder
  `[REDACTED:email:<8-hex>]`; the same address gets the same tag within one run
  and unlinkable tags across runs. The salt lives in the owner-only run
  directory and is deleted by purge. No unsalted (global) hash.
- **OD-3 — Consent does not expire.** `redacted` persists until the owner lowers
  it; `agent-braid lightning status` shows the consent level, `consentedAt` and
  the consented sources. Retention (30 days default, 90 maximum) bounds what
  accumulates.

## Requirements

- **REQ-001 — Consent contract.** `traces.contentConsent` accepts only `none`
  and `redacted`, defaults to `none`, and is changed only by `agent-braid
  lightning init` with a preview showing the sources, retention and effects,
  applied with `--apply --preview-digest`; `plugin setup` only sets `lightning`
  `off` | `lab` and never the consent. The consent fields extend the `traces`
  section of `schemas/0.3.0-experimental/lightning-config.schema.json`, and
  that schema and the validator agree on a corpus.
- **REQ-002 — Refusal without consent.** With consent `none` (or an invalid
  configuration), every content-bearing field is refused by the store with
  the SPEC-070 store refusal `store-consent`, and the adapter emits only
  content-free records; the adapter and CLI report the refusal as
  `content-consent-required`. Both codes are in the contract vocabulary.
- **REQ-003 — Redaction.** `lightning_redact` replaces secrets (literal known
  values and the spec069 `SECRET_PATTERNS`), bearer and OAuth tokens, emails,
  home-directory paths and API-key shapes with typed placeholders; a
  post-redaction scan must be clean or the record is refused.
- **REQ-004 — Canary corpus.** A committed secret-canary corpus covers every
  pattern class in plain, JSON-escaped, URL-encoded, split-across-fields and
  base64 forms; every canary is caught and no canary reaches any output.
- **REQ-005 — Retention and purge.** Content records carry a creation date;
  a sweep deletes records older than `traces.retentionDays` (default 30,
  maximum 90); the BL.0 `agent-braid lightning purge`, extended here, deletes
  all content for a run or
  all runs after a preview; purge leaves no content bytes in the store.
- **REQ-006 — Adapter.** `lightning_adapter` ports `TracerTraceToTriplet` and
  `TraceToMessages` to the standard library: rollout records, host transcripts
  (via `trace_adapter.read_trace`/`import_trace` and the observers), the Loom
  stream (via `view_loom.parse_stream`/`validate_event`) and System One episodes
  (via `system_one_shadow.validate_episode`) become triplets or messages that
  are always redacted and carry source, digest and loss notes.
- **REQ-007 — System One isolation.** The adapter opens System One episode files
  read-only, writes nothing under the shadow directory, and no adapter output is
  accepted as System One input (ADR 0034).
- **REQ-008 — Boundaries.** No socket, no subprocess, standard library only, no
  MCP tool; every CLI output carries `executionAuthorization: false`; telemetry
  stays content-free.

## Success criteria

Each requirement has one acceptance scenario (SC-001 to SC-008) in
[assurance.json](assurance.json), with its procedure in
[validation-plan.md](validation-plan.md). Milestone exit: the secret-canary
corpus is all caught; content is refused without consent; purge and the
retention sweep are tested.

## Compatibility

Additive. Default consent `none` keeps current behaviour. The configuration
schema `braid-lightning-config/v0.1` already declares `traces.contentConsent`
and `traces.retentionDays`; this specification extends that `traces` section
(`consentedAt`, `consentPreviewDigest`) and gives `redacted` its effect. No
separate consent schema is added.
