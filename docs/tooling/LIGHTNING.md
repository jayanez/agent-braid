# Braid Lightning (experimental)

Braid Lightning is an off-by-default laboratory that will improve the guidance
Agent Braid owns (skills, tool descriptions) from recorded rollouts and
verifiable rewards. It adapts [microsoft/agent-lightning](https://github.com/microsoft/agent-lightning)
(MIT) and is planned in the [BL program](../../specs/070-braid-lightning-foundations/program.md).

**Today (BL.0)** you can only configure and inspect it. No run starts, no host is
launched and no model is called.

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
