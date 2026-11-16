# Braid Lightning (experimental)

Braid Lightning is an off-by-default laboratory that will improve the guidance
Agent Braid owns (skills, tool descriptions) from recorded rollouts and
verifiable rewards. It adapts [microsoft/agent-lightning](https://github.com/microsoft/agent-lightning)
(MIT) and is planned in the [BL program](../../specs/070-braid-lightning-foundations/program.md).

**Today (BL.0 and BL.1 closed)** you can configure it, plan runs, run the rollout pipeline against fake hosts
and run Claude Code rollouts on the subscription route. A real host run needs the setup consent and the host
subscription route. Prompt optimization (BL.2, SPEC-072) runs APO and GEPA arms through `agent-braid lightning run`
in the laboratory; its preregistered held-out evaluation (2026-11-13) was negative (no arm met D4, H1 not
supported), so no optimized guidance is promoted or shipped. Dataset export (BL.5, SPEC-075) is
off by default and exports fixture runs only (see below).

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
agent-braid lightning sweep --home "<registryHome>"                # retention (SPEC-074)
agent-braid lightning purge --home "<registryHome>" --run-id <id> | --all   # preview, then add
#   --apply --preview-digest <d> from the preview to delete
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

## Dataset export (BL.5, SPEC-075)

`agent-braid lightning export` writes a local dataset from consented, redacted runs, for a later, separately
approved training step. It never trains, uploads or publishes anything, and it makes no claim that a dataset
or its balance helps any model.

```sh
agent-braid lightning init --home "<registryHome>" --non-interactive --export   # preview; then --apply with its digest
agent-braid lightning export --home "<registryHome>" --run <id> --kind rollout --level trajectory \
  --out <new empty directory> [--dry-run]
agent-braid lightning export --help
```

- **Off by default.** It refuses with `export-disabled` unless the profile has `export.enabled` set by a
  previewed `lightning init --export`. Content consent `redacted` is needed too: without it nothing exports.
- **Host-model output stays closed.** No provider's terms of use have been reviewed (OD-1 is deferred), so any
  run with host-model output refuses with `terms-gate-missing`; only fixture runs (`pipeline-only`) export.
  Agent Braid ships no terms decision record and says no provider permits training. An owner who reviews a
  provider's terms may write their own record under `lightning/terms/` and pass it with `--terms-decision`.
- **Kinds.** `supervised` writes chat `messages` (first-attempt D4 successes only, or every outcome with
  `--outcome-field`) and is never balanced; `rollout` writes turns, the SPEC-071 reward vector and status, and is
  balanced 1:1 per task by default (seeded; `--balance none` to keep everything). `--level transition` is one
  record per model call, `trajectory` one per attempt (text-level merge, declared per record).
- **What the scan catches.** Before anything is written the final bytes are scanned for known secret shapes
  (tokens, bearer headers, private keys, e-mail addresses, your home path) and for any `/Users/<name>` or
  `/home/<name>` path in any case, such as `/home/runner/` or `/srv/home/x`; a hit refuses with
  `canary-detected`. The scan catches known shapes only: a literal secret not given when the trace was stored,
  free text of unknown shape (for example names), a raw id typed in content, encodings nested twice, and
  Windows or doubly escaped paths are not caught.
- **Retention.** Records whose run is past `traces.retentionDays` are excluded and counted as
  `retention-expired`, from the exact expiry instant.
- **Outside purge.** Exported files are not deleted by `lightning purge`; delete them yourself.
  `lightning purge` lists the datasets that cite a purged run (`citingDatasets`), from a small private index
  under the plugin home that holds only each export's path, digest and runs.
- Output: `--out` must be a canonical path without symbolic links (on macOS `/tmp` is one: use `/private/tmp`
  or a directory under your home) that does not exist or is empty; it gets exactly `records.jsonl` and
  `manifest.json` (private files). See the [manifest contract](../../specs/075-lightning-dataset-export/contracts/dataset-manifest.md).
