# Contract: triplets and messages

Produced by `agent_braid/lightning_adapter.py`. Shapes follow agent-lightning
v0.x (`adapter/triplet.py` `Triplet`/`Transition`, `adapter/messages.py`
`OpenAIMessages`) so SPEC-075 can export them.

## Triplet (`braid-lightning-triplet/v0.1`)

| Field | Type | Rule |
|---|---|---|
| `schema` | const | `braid-lightning-triplet/v0.1` |
| `rolloutId` | id | rollout: the SPEC-070 event's rollout id; other sources: `<source>-<first 16 hex of sourceSha256>` |
| `attemptId` | pseudonym | `<kind>-<16 hex>`: HMAC-SHA256 of the raw id in a domain per kind, never the raw id. `attempt-` (rollout attempt id, keyed by the run salt), `turn-` (host-transcript attempt id), `strand-` (Loom strand or operation id), `episode-` (System One episode id), keyed by the salt the caller passes; stable for one salt and value |
| `source` | enum `rollout`, `host-transcript`, `loom`, `system-one` | consented source |
| `sourceSha256` | hex | digest of the source bytes read |
| `prompt` | object `{text}` or null | redacted; null when consent is `none` |
| `response` | object `{text, toolCalls}` or null | redacted; null when consent is `none` |
| `reward` | finite number or null | matched by policy |
| `rewardMatch` | enum `first-occurrence`, `first-sibling`, or null | upstream `RewardMatchPolicy` subset; null for Loom (no reward) |
| `redaction` | object `{classes: {class: count}, scanClean: true}` | always present |
| `losses` | sorted list of strings | fields dropped or unmappable |
| `createdAt` | epoch seconds or null | retention clock: the content record's `createdAt`; null for Loom, which has no store clock |

## Messages (`braid-lightning-messages/v0.1`)

`{schema, rolloutId, source, sourceSha256, messages: [{role, content,
toolCalls?}], redaction, losses, createdAt}`; roles `system`, `user`,
`assistant`, `tool`. With consent `none`, `messages` is empty and `losses`
contains `content-consent-required`.

## Source mapping

| Source | Reader | Unit |
|---|---|---|
| rollout | SPEC-070 `lightning_store` | event spans of one attempt |
| host-transcript | `trace_adapter.read_trace`, `import_trace`; `tooling_claude_observer`, `tooling_codex_observer` | one host turn |
| loom | `view_loom.parse_stream`, `validate_event` | one event chain |
| system-one | `system_one_shadow.validate_episode` (read-only) | one episode |

Rollout content records (`trace` kind in the run store, T006) carry
`{attemptId, sequence, prompt, response, toolCalls?}`; `sequence` names the
`model_request` event they belong to. One triplet is produced per
`model_request`; Loom yields one triplet per strand (label as prompt, tools and
outcome as response) and one `system` message per event. In those messages
each strand or operation reference at its `view_loom` schema position
(`strandId`, `parentStrandId`, `waitingOn`, `left`, `right`, `strands[*]`,
`waves[*][*]`, `units[*]`) is replaced by the same `strand-` pseudonym the
triplet uses; no other field (`reportId`, `planId`, `scheduleId`,
`manifestDigest`, labels, tool names) is renamed, and two ids whose
pseudonyms collide refuse the stream with `source-invalid`. A host transcript
yields one triplet per host turn (its tool as the tool call; recorded traces
hold no prompt or model text; `trace_adapter` admits synthetic traces only, so
real host transcripts are not read yet), named by a salted turn pseudonym in
source order, and one `system` message per turn. A System One
day file, opened read-only, yields one triplet per episode (System 2 pairs as
prompt, System One answer as response; no outcome is joined, so no reward) and
a `user` and `assistant` message per episode; an invalid or torn line is
skipped and noted as `episode-invalid`, as the System One report counts it.

Reward matching: `first-occurrence` gives each reward event to the nearest
earlier `model_request` without a reward; `first-sibling` gives the attempt's
first reward to its first `model_request`.

Loss notes: `content-consent-required`, `content-missing`, `content-duplicate`
(a second record for one request; the first is kept), `content-refused`
(the run holds a refused stub; stubs carry no attempt, so the note is run-level), `prompt-missing`, `response-missing`,
`reward-unmatched`, `reward-unavailable` and `model-text-unavailable` (Loom),
`outcome-missing` (an open strand). A source that does not parse is refused
with `source-invalid`; an unclean result with `redaction-incomplete`; a
missing or unreadable run with its store code (for example `store-missing`);
a salt shorter than 16 bytes with `salt-invalid`. Refusal texts are fixed and
name no source value (an id, path or parser message), only a closed reason
code or source name. Source refusals (rollout, host transcript, Loom, System
One, run store, salt) are raised without a chained cause; `redaction-incomplete`
keeps the redactor's error as its cause, whose text names redaction classes
only.

Outputs are deterministic for the same inputs and salt; canonical JSON bytes.
