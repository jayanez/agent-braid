# Contract: triplets and messages

Produced by `agent_braid/lightning_adapter.py`. Shapes follow agent-lightning
v0.x (`adapter/triplet.py` `Triplet`/`Transition`, `adapter/messages.py`
`OpenAIMessages`) so SPEC-075 can export them.

## Triplet (`braid-lightning-triplet/v0.1`)

| Field | Type | Rule |
|---|---|---|
| `schema` | const | `braid-lightning-triplet/v0.1` |
| `rolloutId`, `attemptId` | id | from the SPEC-070 data model |
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
outcome as response) and one `system` message per event.

Reward matching: `first-occurrence` gives each reward event to the nearest
earlier `model_request` without a reward; `first-sibling` gives the attempt's
first reward to its first `model_request`.

Loss notes: `content-consent-required`, `content-missing`, `content-duplicate`
(a second record for one request; the first is kept), `content-refused`
(the run holds a refused stub; stubs carry no attempt, so the note is run-level), `prompt-missing`, `response-missing`,
`reward-unmatched`, `reward-unavailable` and `model-text-unavailable` (Loom),
`outcome-missing` (an open strand). A source that does not parse is refused
with `source-invalid`; an unclean result with `redaction-incomplete`.

Outputs are deterministic for the same inputs and salt; canonical JSON bytes.
