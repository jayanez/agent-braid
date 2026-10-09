# Bounded M4 alpha implementation and validation

SPEC-021 and ADR 0020 scope are adopted. On 2026-10-09 the founder accepted
bounded M4 alpha engineering and evaluation as complete with a negative-utility
result. The historical G4 NO-GO on useful speedup remains unchanged; this is not
a general utility, semantic-correctness, production-safety or scientific claim.
See the [whole-M4 decision](../038-m4-real-workload-closure/whole-m4-founder-decision-20261009.json)
and [closure packet](../038-m4-real-workload-closure/whole-m4-closure-packet.md).
Current GitHub tracking is shown in the [live M4 milestone](https://github.com/jayanez/agent-braid/milestone/6).
Use the existing isolated Python >=3.12 environment.
The adapter has no new runtime dependencies.

## Local operator pipeline

Start with an owned fixed-patch request and verified portable evidence/advisory plan:

```sh
python -m agent_braid prepare-policy-run request.json \
  --run-directory /owned/results/run-one --evidence replay.json \
  --advisory-plan advisory.json --mode parallel > policy-plan.json
python -m agent_braid verify-policy-plan policy-plan.json
```

Preparation does not allocate the persistent result or authorize execution. The
operator reviews the full plan, inputs, private destination, policy and phase
budgets, then acknowledges its exact planDigest through the local operator path:

```sh
python -m agent_braid grant-policy-run policy-plan.json \
  --grant-store /owned/grants --acknowledge '<exact planDigest>' > grant.json
python -m agent_braid execute-policy-run policy-plan.json \
  --grant-store /owned/grants --grant-id '<locally issued grantId>'
python -m agent_braid inspect-policy-run policy-plan.json --grant-store /owned/grants
```

The store must be owned 0700 and outside source/common Git/private-result storage.
A consumed grant never executes twice. A prefix requires a new explicit grant with
--action resume or abort and recover-policy-run with the matching action. A missing
run after consumption requires operator inspection. The tool path cannot issue
grants, and returned digests/annotations cannot replace operator acknowledgement.
The serial revision remains available by omitting --mode parallel.

## Stdio MCP launch

Configure canonical roots explicitly, without persistent host registration:

```sh
python -m agent_braid.mcp_runtime --source-root /owned/source \
  --result-parent /owned/results --grant-store /owned/grants
```

The only advertised tools are analyze, prepare, status, execute, recover and verify.
The server owns stdin/stdout as bounded protocol channels; stdout is not a diagnostic
stream. Tool callers must use the configured canonical source and direct-child
result paths. No network listener, arbitrary command, source promotion or authorize
registry entry is admitted. See c3-implementation.md for error/cancellation limits.

## Candidate gates

Run quick after a coherent increment and pr once on a stable candidate. Fresh
reproduction and measurement require a clean frozen checkout and output outside it:

```sh
python -m scripts.reproduce_m4_alpha --output /owned/evidence/reproduction.json
python -m scripts.measure_m4_alpha --output /owned/evidence/measurement.json
python -m scripts.capture_m4_codex --codex-path /path/to/pinned/codex \
  --output /owned/evidence/codex.json
```

Codex capture uses its actual direct MCP bridge, ephemeral sessions, owned fixtures
and no model turn. It tests refusal, controlled checkpoint disconnect, new-grant
resume, duplicate delivery and abort. It does not modify persistent host config.
Claude Code host capture uses a temporary MCP JSON config containing only `m4_alpha`
and `--strict-mcp-config`; disable built-in tools so the model can reach only the
bounded adapter. Authenticate with `claude.ai` (`claude auth status` should identify
the subscription provider), turn usage credits off under Claude Settings > Usage,
and remove API/provider overrides from the capture process environment. Do not
continue through Console/API fallback when the included subscription limit is met.

The CLI supports a streaming, multi-turn session so the operator can inspect the
prepared plan before issuing a local grant and can resume the same session after an
intentional disconnect:

```sh
claude --model sonnet --mcp-config "$M4_TEMP_CONFIG" --strict-mcp-config \
  --tools "" \
  --allowedTools mcp__m4_alpha__analyze mcp__m4_alpha__prepare \
    mcp__m4_alpha__status mcp__m4_alpha__verify \
    mcp__m4_alpha__execute mcp__m4_alpha__recover \
  --input-format stream-json --output-format stream-json --verbose \
  --permission-mode acceptEdits --max-turns 5 -p
```

Send each user turn as one JSONL `user` message. Keep execute/recover grants out of
MCP: after inspecting the exact plan digest, the operator issues the one-use grant
through the local path; recovery needs a separate resume/abort grant. Evidence for
the actual Claude Code 2.1.236 exercise is in `host-evidence/claude.json`. The
capture changed no persistent host MCP configuration or candidate source. No new
hosts, credentials or dependencies are installed by these commands.

The manual Linux workflow is prepared for publication only after separate authority
is given. It uses no live-model credentials. A successful profile, local reproduction
or host capture does not close the six roadmap rows. Consult closure-matrix.md,
measurement-protocol.md and the exact-candidate review packet; independent Luna
The founder's bounded whole-M4 acceptance is recorded in the linked decision
above. The historical G4 NO-GO and all evidence limits remain in force; tracking
reconciliation is a separate pending administrative step.
