# Bounded M4 alpha implementation and validation

SPEC-021 and ADR 0020 scope are adopted. Implementation acceptance and whole-M4
closure remain separate gates. Use the existing isolated Python >=3.12 environment.
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
Claude model-backed tool exercises require the separately agreed consumption budget.
No new hosts, credentials or dependencies are installed by these commands.

The manual Linux workflow is prepared for publication only after separate authority
is given. It uses no live-model credentials. A successful profile, local reproduction
or host capture does not close the six roadmap rows. Consult closure-matrix.md,
measurement-protocol.md and the exact-candidate review packet; independent Luna
review and founder whole-M4 acceptance remain distinct.
