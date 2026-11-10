# Braid Lightning (experimental)

Braid Lightning is an off-by-default laboratory that will improve the guidance
Agent Braid owns (skills, tool descriptions) from recorded rollouts and
verifiable rewards. It adapts [microsoft/agent-lightning](https://github.com/microsoft/agent-lightning)
(MIT) and is planned in the [BL program](../../specs/070-braid-lightning-foundations/program.md).

**Today (BL.0 closed, BL.1 delivered with fake hosts)** you can configure it, plan runs and run the full
rollout pipeline against fake hosts. A real host run needs the setup consent, the host subscription route and,
for the first baseline, the owner's explicit yes.

## Opt in during setup

```sh
agent-braid plugin setup --home "<registryHome>" --lightning lab
agent-braid plugin setup --home "<registryHome>" --lightning lab --apply --preview-digest <digest>
```

`--lightning off` removes the consent. Earlier plugin versions refuse a registry
that records `lab`.

## Configure the laboratory

```sh
agent-braid lightning init --home "<registryHome>"
```

The wizard asks seven questions (guidance file, hosts, algorithm, repetitions,
rollout budget, trace content consent, export) and prints a preview with an
`applyWith` command line. Run that command to write the profile; a changed
profile or a wrong digest is refused. Non-interactive use takes the same answers
as flags (`--non-interactive --hosts opencode --algorithm apo …`).

| Upstream trainer option | Braid Lightning |
|---|---|
| model path | `target.path` (a guidance file; no weights) |
| train / validation datasets | `data.train`, `data.holdout` |
| `n_runners`, strategy | `rollout.parallel` (default 1) |
| algorithm (APO, VERL) | `algorithm.name`: `gepa`, `apo`, `baseline` |
| `max_rollouts` | `budget.maxRollouts`, `budget.maxOptimizerCalls` |
| tracer, adapter | `traces.*`, `export.level` |
| Kubernetes, gateway ports, GPU trainer | not offered |

Fixed values: extra cash spend `eurCap` 0, model route `subscription` (any
`*_API_KEY` is refused), promotion `human`, `executionAuthorization` false. The full
contract is [lightning-config.md](../../specs/070-braid-lightning-foundations/contracts/lightning-config.md).

```sh
agent-braid lightning validate --home "<registryHome>"
agent-braid lightning status --home "<registryHome>"
agent-braid lightning purge --home "<registryHome>" --run-id <id> | --expired
```

## Rollouts and verifiable reward (BL.1, SPEC-071)

```sh
agent-braid lightning run --home "<registryHome>" --dry-run       # plan only; launches nothing
agent-braid lightning run --home "<registryHome>" --fake-hosts    # full pipeline, labelled pipeline-only
agent-braid lightning status --home "<registryHome>" --run-id <id>
agent-braid lightning report --home "<registryHome>" --run-id <id>  # per-host Wilson intervals, replayed rewards
agent-braid lightning run --home "<registryHome>" --resume <id>   # only after a budget or quota stop
```

- **Subscription only.** The run is refused (`paid-route-refused`) if any `*_API_KEY`,
  `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL` or Bedrock/Vertex switch is in the environment. Claude Code
  uses `CLAUDE_CODE_OAUTH_TOKEN` (create it with `claude setup-token`; export it with `read -rs` in your own
  terminal). The host-reported `apiKeySource` is recorded for every rollout.
- **OpenCode** reports no credential source today, so it ends as `route-unverified` and is a declared limit.
- **Reward** is a vector computed by the frozen SPEC-069 rules: schema validity, D4 at the first attempt and
  within one retry, canary hits. No model judges it. Records keep hashes and content-free parsed attempts, so
  `report` recomputes every reward.
- **Stops.** `budget.maxRollouts` ends a run with `unit-cap`; a host quota message ends it with
  `five-hour-headroom` or `weekly-stop`. Nothing resumes automatically.
- The laboratory runs from an Agent Braid checkout (it uses the SPEC-069 prompt sets, fixture and driver).

