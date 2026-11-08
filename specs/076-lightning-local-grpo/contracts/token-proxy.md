# Contract: Lightning token proxy (proposed, deferred)

Module: `agent_braid/lightning_proxy.py`. Port of upstream v1.0.3
`agentlightning/server/proxy.py` concepts onto `agent_braid/view_serve.py`.

## Binding and authentication

- Binds only `view_serve.LOOPBACK_HOSTS` (127.0.0.1, ::1); otherwise
  `bind-refused`.
- Bearer owner token from an owner-only token file (same rules as the viewer);
  missing or wrong token: 401, no body echo.
- Bodies parsed with `view_serve.parse_json_body` (duplicate keys, non-finite
  numbers and depth refused) and read with a deadline and size bound.
- Upstream backend: a loopback vLLM URL only; a non-loopback backend is refused.

## Routes

| Route | Behaviour |
|---|---|
| `POST /v1/chat/completions` | forwards with `return_token_ids: true`, `logprobs: true`; header `X-Braid-Rollout` and `X-Braid-Attempt` required |
| `POST /pause` | sets paused; new calls get 503 `{"error":"gateway paused","reason"}` with `Retry-After`; waits for in-flight to drain |
| `POST /resume` | clears paused |
| `GET /health` | `{paused, inflight}` |

## Event record

Each call appends a `model_request` event (schema
`braid-lightning-event/v0.2`, host `local-vllm`; v0.1 events stay readable;
recorded by ADR 0042) to the SPEC-070 store: `rolloutId`, `attemptId`,
`sequence`, `model`, `promptTokenIds`, `responseTokenIds`,
`promptTokenIdsSha256`, `responseTokenIdsSha256`, `logprobsSha256`,
`requestSha256`, `responseSha256`,
`status` (`ok` \| `token-ids-missing` \| `upstream-error`). Bytes via
`trace_adapter.canonical_bytes`.

## Retries

Upstream retryable status (429, 5xx) retried with bounded backoff; each try
recorded. No `*_API_KEY` is read or forwarded.
