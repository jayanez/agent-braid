# SPEC-069 native-run runbook (T013, REQ-013)

One command measures whether host models author valid `analyze-work` requests. This runbook says how
to run it, what it automates, what stays manual and why, and what each host does headless (probed
2026-11-07 on macOS arm64; Claude Code 2.1.292, OpenCode 2.1.4, Codex 0.167.0-alpha.3.2).

## Run it

```bash
# once, in your own terminal (never paste a key into a chat or a file)
read -rs ANTHROPIC_API_KEY && export ANTHROPIC_API_KEY
read -rs OPENAI_API_KEY && export OPENAI_API_KEY

python -m scripts.spec069_native_runs --arm baseline --prompt-set development --repetitions 3 \
    --model claude-code=<id> --model opencode=anthropic/<id> --model codex=<id> \
    --output specs/069-aim-request-authoring/evidence/native-runs-baseline.json
```

### Other access paths (D13), when API credit is not available

Four independent switches; combine them freely. The default (keys from the environment) is unchanged.

| Switch | What it does | One-time manual step |
| --- | --- | --- |
| `--model opencode=openrouter/anthropic/claude-sonnet-5-5` | OpenCode through OpenRouter: the driver injects `OPENROUTER_API_KEY` into the OpenCode child only and writes the `openrouter` provider (key as `{env:OPENROUTER_API_KEY}`, never the value) plus the pinned id as a custom model into the redirected XDG config. Evidence: `route: openrouter` and a note | store the key (below) |
| `--keys-from-keychain` | the driver reads each host's key itself with `security find-generic-password -s NAME -w`: `agent-braid-anthropic` (Claude Code, OpenCode direct), `agent-braid-openai` (Codex), `agent-braid-openrouter` (OpenCode via OpenRouter). The environment is **not** consulted in this mode. A missing item is a declared limit for that host, never a prompt | `security add-generic-password -a "$USER" -s agent-braid-openrouter -w` (the `-w` with no value asks for the secret on the terminal, so it is never in shell history) |
| `--auth subscription --auth-profile-dir DIR` | Claude Code and Codex use the owner's subscription through a sign-in kept in `DIR` (recorded as `auth: interactive-once`). OpenCode keeps using a key | the one-time sign-ins (below) |
| `--auth token` | Claude Code only: a long-lived subscription OAuth token (from `claude setup-token`) is injected as `CLAUDE_CODE_OAUTH_TOKEN` into the Claude Code child only; no `ANTHROPIC_API_KEY` is set for that child and no profile credential file is used. Evidence: `auth: oauth-token-env`, `keySource: keychain` or `environment`, plus a note. With `--keys-from-keychain` the token is read from the keychain item `agent-braid-claude-oauth` (the environment is not used); otherwise from the driver's `CLAUDE_CODE_OAUTH_TOKEN`. Codex and OpenCode keep their own routes. A missing token is a declared limit for Claude Code | the one-time token (below) |

```bash
# keys, once each (prompted without echo)
security add-generic-password -a "$USER" -s agent-braid-anthropic -w
security add-generic-password -a "$USER" -s agent-braid-openai -w
security add-generic-password -a "$USER" -s agent-braid-openrouter -w

# Claude Code token (resolves the keychain caveat), once, in your own Terminal.app, never in chat:
claude setup-token        # complete the browser sign-in; copy the token it prints
security add-generic-password -a "$USER" -s agent-braid-claude-oauth -w    # paste the token at the silent prompt
python -m scripts.spec069_native_runs --check-login claude-code --auth token --keys-from-keychain

# subscription sign-in, once per host: the driver prints the exact command, you run it in Terminal.app
python -m scripts.spec069_native_runs --login claude-code --auth-profile-dir ~/agent-braid-auth   # then /login in Claude Code
python -m scripts.spec069_native_runs --login codex       --auth-profile-dir ~/agent-braid-auth
python -m scripts.spec069_native_runs --check-login claude-code --auth-profile-dir ~/agent-braid-auth
python -m scripts.spec069_native_runs --check-login codex       --auth-profile-dir ~/agent-braid-auth

# a run with no API credit (Claude Code by token; use --auth subscription instead for Codex's sign-in)
python -m scripts.spec069_native_runs --arm baseline --prompt-set development --repetitions 3 \
    --auth subscription --auth-profile-dir ~/agent-braid-auth --keys-from-keychain \
    --model claude-code=<id> --model codex=<id> --model opencode=openrouter/anthropic/claude-sonnet-5-5 \
    --output specs/069-aim-request-authoring/evidence/native-runs-baseline.json
```

- `--login HOST` only prints the command (`CLAUDE_CONFIG_DIR=<DIR>/claude claude`, then `/login`; or
  `CODEX_HOME=<DIR>/codex codex login`). It starts nothing, creates nothing, and the driver never reads a terminal.
- `--check-login HOST` looks at the host's credential file by existence and size only (`.credentials.json` /
  `auth.json`; the file is never opened), then sends one trivial headless prompt under the same OS sandbox as a
  run. It prints JSON (`ok`, credential presence and size, sandbox probe) and exits `0` when the host answered.
  No credential file at all with a working prompt means the session is held elsewhere (see the keychain caveat).
- The sign-in directory must be outside the repository and must not be, contain or lie under (also through a
  symlink) `~/.claude`, `~/.codex`, `~/.config/opencode` or any other protected real path: the run is refused
  with a safety stop (`2`) before any host starts. It is created `0700`, reused across runs and **not** deleted by
  teardown. The OS sandbox still denies the real configuration directories, Keychains, `.ssh` and `.aws`; a probe
  also checks that `DIR/<host>` can be listed and written under it.

- `--arm baseline` builds develop commit `8f63c606` (alpha.7 runtime plus the PR #1099 guidance) in a
  temporary git worktree; `--arm final` builds this checkout; `--arm final-no-schema` (D9 ablation) builds the
  committed `HEAD` with only the request schema reverted to the interim description
  (`spec069_tool_schemas --delivery description-only`; dirty by construction, recorded as `sourceDirty`, with
  `delivery` and the SHA-256 of the generated schema module in the evidence `candidate`). Run `final` and
  `final-no-schema` with the same prompt set, models and repetitions; the schema is kept only if first-attempt
  validity improves in at least one host. `--plugin-dir <plugins/agent-braid>` uses a
  prebuilt plugin instead (the build needs `uv` and Python 3.12; the runtime tarball cache is
  `$TMPDIR/agent-braid-spec069-build-cache`).
- `--prompt-set` is a set id under `prompts/` or a path. The held-out set is run by the driver only.
- `--hosts`, `--limit-cases N`, `--codex-bin`, `--claude-bin`, `--opencode-bin`, `--timeout`,
  `--max-turns` are probes and overrides. Pin every model (D9): OpenCode refuses to run unpinned.
- Exit codes: `0` completed (a host that cannot run is a declared limit, still `0`); `2` safety stop
  (leaked real path, isolation probe failed, a denied tool ran); `3` teardown found a leftover profile or
  process; `4` secret scan refused the evidence.
- `--fake-hosts` runs the identical pipeline against `tests/fixtures/spec069-fake-hosts/`. Its evidence
  says `"label": "pipeline-only"`: it proves the driver, not any host or model. CI runs it through
  `tests/test_spec069_native_runs.py`.

Evidence: `<output>.json` plus `<output>.transcripts/<host>/<case>-r<n>.jsonl`; every transcript has a
SHA-256 in the evidence; prompt-set, driver and scoring hashes are recorded. Nothing is written until the
secret scan passes.

## What is automated

Candidate build; disposable profile per host under a private (`0700`) temp root with `HOME`, XDG,
`CLAUDE_CONFIG_DIR` / `CODEX_HOME` redirected and a minimal environment (no inherited variables); fixed
sandbox git workspace; plugin install per host; workspace registration with `plugin setup --apply`
(telemetry local); every prompt through the host's headless mode; parsing of the ordered `analyze-work`
attempts; scoring; redaction and secret scan; evidence with hashes; teardown and a check that no profile
or process remains (a straggler is detected, reported and killed).

Safety (A10), each with a negative control in the self-test:

| Control | How | Negative control |
| --- | --- | --- |
| Only Agent Braid tools | Claude: `--allowedTools` / `--disallowedTools`; OpenCode: permission deny for built-ins; Codex: read-only sandbox, approval never. Any other tool that runs stops the host | denied tool refused (recorded); denied tool that runs stops the run |
| Real config unreachable | macOS `sandbox-exec` denying `~/.claude`, `~/.codex`, `~/.config/opencode`, other OpenCode dirs, Keychains, `.ssh`, `.aws`; canary file read through the redirected home; denied-access probe on every existing real path before the first prompt | a real path in an argument or environment value stops the run before any host starts |
| No secret in evidence | keys come from this process's environment only; known values and credential patterns are redacted in transcripts, stderr and attempts; a scan runs over everything before writing | a planted secret echoed by the fake host is absent; the scan refuses a leaking file |
| Clean teardown | process groups killed, profile removed, then verified | leftover profile and detached process are detected |

## What stays manual, and why

| Step | Reason |
| --- | --- |
| Token mode only: `claude setup-token` and `security add-generic-password -a "$USER" -s agent-braid-claude-oauth -w` in your own Terminal.app (silent prompt) | D13: the driver never reads a terminal or prompts for, writes or logs a token |
| Store the API keys once: macOS keychain items (`--keys-from-keychain`) or `export` in your own terminal | D13: the driver never prompts for, writes or logs a key |
| Subscription mode: the one-time sign-in per host in your own Terminal.app (`--login HOST` prints the command) | the driver never reads a terminal, a credential file or a password |
| Install Codex when the ChatGPT desktop bundle is missing | the driver does not install host applications (D11) |
| Decide on results and on the release (REQ-012) | owner decisions (D5) |

A missing key, a missing binary, an unpinned OpenCode model, a failed plugin install or a host that
fails before the model answers (for example a rejected key) is reported as a **declared limit** for that
host, never as a negative result and never as a request to paste anything.

## Comparability and limits of the other access paths

- **OpenRouter.** The model is the same but the route is not: OpenRouter picks the upstream provider, caching
  and latency differ, and cost is not reported (`cost: 0`). Results are labelled `route: openrouter` and are **not
  strictly comparable** with a direct-API baseline. Keep the baseline and final arms on the same route; do not
  compare an `openrouter` arm with a `direct` arm without saying so. OpenCode's JSON stream names no model, so
  `modelsObserved` is empty and the pinned id is the identity. OpenCode's catalogue spells ids with dots
  (`claude-sonnet-5.5`) while OpenRouter serves `anthropic/claude-sonnet-5-5`, so the driver declares the pinned
  id as a custom model (without it OpenCode answers `Model unavailable`). Probed 2026-11-11 with one prompt:
  valid first attempt.
- **Subscription.** Runs consume the owner's subscription allowance and are subject to its rate limits;
  automated headless use may be restricted by the provider's terms, and a sign-in can expire (run
  `--check-login` again; the driver reports a host that cannot answer as a declared limit, never a result).
  Evidence says `auth: interactive-once`. Subscription and API-key runs may differ in default model, system prompt
  and limits: pin the model and keep one arm pair on one access path.
- **Keychain caveat (observed, resolved by `--auth token`).** On macOS, Claude Code keeps its session in the
  keychain rather than in `.credentials.json`, and the driver redirects `HOME` for every host, so
  `--check-login claude-code --auth-profile-dir ...` fails even after a completed `/login`. The implemented
  alternative is counterfactual C5: a long-lived token through the environment (`--auth token`). Token mode
  checks presence and length only (never the value), then sends one trivial headless prompt under the run's OS
  sandbox; an absent token or a rejected or expired one is reported as a declared limit, never a result. Run it
  again after `claude setup-token`. Whether `--check-login` passes on a given machine is only proven once the owner
  has stored the token. Codex keeps `auth.json` in `CODEX_HOME`. Codex also writes its plugin install state into
  the same reusable directory, so a re-run reinstalls over it.
- **Subscription and API runs may differ.** A token run bills to the subscription allowance and may use a different
  default model, system prompt and limits than an API-key run: pin `--model claude-code=<id>` and keep one arm
  pair (baseline and final) on one access path. The token shape (`sk-ant-oat...`) is redacted and secret-scanned
  in transcripts and evidence like every other credential.
- With `--keys-from-keychain`, `--auth subscription` or `--auth token` an inherited `ANTHROPIC_BASE_URL` is not forwarded (it
  belongs to the environment key).

## Host findings

| Host | Headless mode | Key | Installed how | Status |
| --- | --- | --- | --- | --- |
| Claude Code | `claude -p ... --output-format stream-json --verbose` | `ANTHROPIC_API_KEY` | `--plugin-dir` | verified end to end through the driver (1 prompt, haiku): valid first attempt |
| OpenCode | `opencode run --standalone --format json -m anthropic/<id>` | `ANTHROPIC_API_KEY` | `opencode plugin add git+file://...#candidate::path:plugins/agent-braid` into the redirected XDG config | verified end to end through the driver (1 prompt, haiku): valid first attempt |
| Codex | `codex exec --json --skip-git-repo-check -s read-only -c approval_policy="never"` | `CODEX_API_KEY` (the driver maps `OPENAI_API_KEY` to it) | `codex plugin marketplace add <build output>` then `codex plugin add agent-braid@agent-braid` into a disposable `CODEX_HOME` | install, registration, sandbox and launch verified with the real binary; the authenticated model call and the MCP transcript shape are **unverified**: no OpenAI key was available in the session that built the driver |

All three run headless. Observations that shaped the driver:

- **Codex key name.** `codex exec` returns `401 Missing bearer` with `OPENAI_API_KEY` set and uses the key
  with `CODEX_API_KEY` (a fake value produced `Incorrect API key`). The driver injects `CODEX_API_KEY`.
  Codex needs a disposable `CODEX_HOME`: a fresh one reports `Not logged in` and holds no credentials.
- **Codex MCP environment.** The plugin server receives `PLUGIN_ROOT` and `PLUGIN_DATA`; whether
  `AGENT_BRAID_HOME` reaches it is unverified, so the driver sets `HOME` too and the default state root
  follows `HOME`. If a real Codex run cannot see the registered workspace, that is the first suspect.
- **OpenCode background service.** Without `--standalone`, `opencode` talks to a managed service on a
  fixed port (49374). On a machine where the owner's service runs, that would be the owner's service
  and configuration. The driver always passes `--standalone`; `opencode plugin add` has no such flag but
  only writes the redirected XDG config (checked: the real `opencode.json` mtime did not change).
- **OpenCode default model.** With no key, `opencode run` silently answers from a free hosted model
  (`opencode/*`). The driver requires a pinned `anthropic/<id>`.
- **OpenCode plugin config key** is `plugins` (not `plugin`). Agent Braid tools are named
  `agent-braid_<tool>`. In one probe a small model did not call them until it used the built-in
  `execute` tool first; `execute` runs JavaScript with `fetch`, so the driver treats it as a discovery
  helper, records every call and classifies any use of `fetch(`, `require(` or `import(` as a denied
  tool. A deny-by-default permission (`"*": "deny"`) hid the Agent Braid tools, so individual built-ins
  are denied instead. Whether `execute` discovery lowers or raises validity is a result to read, not hide.
- **Claude Code** needs `ToolSearch` (deferred MCP schemas) and `Skill` (the plugin's packaged guidance,
  part of what is measured); both are recorded as helper calls, not as attempts. Cost in the smoke run:
  about 0.17 USD for one prompt with a small model; budget `prompts x repetitions x hosts` times the
  model's price (30 runs per host at D9's three repetitions).
- **Canonical paths.** Agent Braid refuses symlinked paths; macOS temp directories sit behind
  `/var -> /private/var`, so the profile root is resolved first.
- The plugin treats registry changes as needing a reconnect: workspaces are registered before the host
  starts, never during a run.

## Limits

- Evidence from this task's smoke runs (one prompt, small models, the current checkout) shows the
  pipeline works against the real Claude Code and OpenCode; it is **not** REQ-010 evidence and no baseline
  or final run has been made.
- The OS sandbox is macOS `sandbox-exec`. On Linux it is unavailable: a real run is refused there
  (use `--no-os-sandbox` only for an engineering probe) and the self-test records the sandbox as `none`.
  Network access is not restricted: the hosts need their API.
- Teardown detects stragglers by the profile path in their command line, plus the process groups the
  driver started.
- The driver does not run on Windows.

## Host probe of the nested per-kind schema (T005 gate)

```sh
python -m scripts.spec069_native_runs --arm final --record-mcp \
  --model claude-code=<id> --model opencode=anthropic/<id> --model codex=<id>
```

`--record-mcp` instruments the candidate actually installed in the driver's disposable host profile and
uses the development prompt set by default. Its
hash-only receipts cover each observed stdio connection, negotiated protocol version, `tools/list` identity,
and the `request` JSON type reaching `analyze-work`; fake hosts are rejected for this mode. This does not
itself prove that a listed tool was exposed to or loaded by the model. The current relay does not observe
model API requests, so eager/deferred schema loading remains unobserved until a separate approved method
captures that boundary. Compare canonical definition hashes within the same protocol version and verify
the host transcript and receipt agree on calls; a missing connection or incomplete receipt is not a pass.

**Do not run this command yet unless a preventive, independently verified EUR 25 per-pass spending limit
covers every route and the maximum in-flight call.** The driver has no such hard cap; prompt counts,
turn limits, timeouts and post-call cost checks are insufficient. This command is a paid native-host run,
not an offline validation command. A host without credentials or whose call cannot complete is a declared
limit, never a pass. After the spend gate is resolved, query all local real-use sources listed in
`docs/development/REAL_USE_EVIDENCE.md` before treating the run as real-use verification or preparing an
approval packet.

### Native schema probe through the product (`--probe-schema`, T005)

```bash
python -m scripts.spec069_native_runs --probe-schema --arm final --hosts claude-code,opencode --auth token --keys-from-keychain \
    --model claude-code=claude-sonnet-5-5 --model opencode=openrouter/anthropic/claude-sonnet-5-5 \
    --output specs/069-aim-request-authoring/evidence/native-probe-schema-per-kind.json
python -m scripts.spec069_native_runs --probe-schema --arm final --hosts codex --auth subscription --auth-profile-dir ~/agent-braid-auth \
    --output specs/069-aim-request-authoring/evidence/native-probe-schema-per-kind-codex.json
# description-only arm: the same two commands with --arm final-no-schema and -description-only in the output names
```

The real plugin, not the test double above: the driver moves `launch` to `launch.real` in the disposable installed copy (Claude
Code gets a copy of the build; Codex's install in the reusable sign-in directory is restored after the run) and installs a wrapper
that runs `scripts/spec069_stdio_proxy.py --keep-listing` for `plugin serve` only. One prompt asks for an `aim` call with
`examples/analysis/file-edits.json` and a `units` call. The evidence `schemaProbe` per host records each connection's protocol
version, the raw `tools/list` line (saved under `<output>.transcripts/<host>/`) and its hashes, the model-facing fingerprint check
against `listed_sizes()`, the `kind` and object/string type of every request at the server, and the verdict; `crossHost`
compares the definition within each protocol version. A stringified or hidden request is a `declared-limit` verdict
(description-only fallback), never a pass. `--fake-hosts --probe-schema` is the self-test (variant `stringify`).

Spend: `--probe-schema` has no preventive cap either; it bounds exposure by design (one prompt, one session per host and
arm, `--repetitions 1` enforced). The 2026-11-13 T005 run was authorized under the SPEC-069 60 USD budget and cost 0.38 USD
notional on Claude Code (token); OpenRouter and Codex reported no cost. It is a host probe, not real-use verification.
