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
| Export the API keys in your own terminal | D13: keys are read from the environment only; the driver never prompts for, writes or logs one |
| Install Codex when the ChatGPT desktop bundle is missing | the driver does not install host applications (D11) |
| Decide on results and on the release (REQ-012) | owner decisions (D5) |
| One-time sign-in into a dedicated profile | only if a host has no environment-key mode. None needs it: all three accept a key. Not implemented because it is not needed |

A missing key, a missing binary, an unpinned OpenCode model, a failed plugin install or a host that
fails before the model answers (for example a rejected key) is reported as a **declared limit** for that
host, never as a negative result and never as a request to paste anything.

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
python -m scripts.spec069_host_probe --model claude-code=<id> --model opencode=anthropic/<id> --model codex=<id>
```

Needs `jsonschema` (the dev requirements), the same environment keys as the driver and no plugin build: a
recording stdio test double serves the candidate's model-facing `analyze-work` definition. It writes
`evidence/host-probe-nested-schema.json` (listing, byte identity by canonical SHA-256, call conformance,
eager or deferred loading from a tool-name-and-hash-only forwarder to the Anthropic API). A host without a
key, or whose model calls the API cannot pay for, is a declared limit or `modelAnswered: false`, never a pass.
