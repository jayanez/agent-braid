# Local forecasting operations

Forecasting is off by default and returns heuristic numeric advice with
`executionAuthorization=false`. Install the core wheel in an isolated Python
3.12+ environment. Core dependencies remain empty. Import, help, discovery and
baseline prediction do not import Torch or download artifacts.

```sh
agent-braid forecast capabilities
agent-braid forecast predict owned-request.json
agent-braid forecast advice owned-advice-request.json
agent-braid forecast inspect owned-receipt.json
agent-braid forecast export owned-receipt.json --output new-export.json
agent-braid forecast serve-mcp
```

The library entry point is `agent_braid.forecast_advice.ForecastSession`.
Requests and independent receipts are versioned; see the
[interface](../../specs/045-local-forecasting-capabilities/contracts/interface.md).
The MCP server uses local stdio and protocol `2025-11-25`, with capabilities,
prediction, advice and inspection tools. It has one active tool call, zero
queue, cancellation by request ID, bounded frames, and cleanup on EOF. Numeric
tool arguments cannot select paths, operator grants, authority or deployments.
Inspection validates schema and content hash only; it explicitly does not
verify source authority or unavailable input bindings.

## Approved CPU deployment

The image lock pins the official Linux ARM64 Torch `2.14.1+cpu` wheel by URL
and hash. Validate `pip check`, explicit Torch/Chronos class imports and the
CPU binary before requesting checkpoint loading. The worker checks both the
distribution version and absence of a compiled CUDA backend before constructing
the pipeline. An installed package metadata/stub smoke alone cannot establish
that its native runtime imports successfully. A changed image, wheel or lock
needs a new exact artifact decision; preserve earlier failed attempts.

The optional `forecast` extra identifies the pinned Chronos package; the complete
[Linux ARM64/Python 3.12 lock](../../specs/045-local-forecasting-capabilities/runtime/requirements-cpu-linux-arm64-py312.lock)
belongs inside the [local image](../../specs/045-local-forecasting-capabilities/runtime/Dockerfile).
Do not install this ML closure into the core environment. Build the wheel, place
it beside the Dockerfile and lock, and build the exact base image. Record Docker's
immutable image configuration ID, the lock SHA256 and both checkpoint hashes.
Preparing a dependency image does not approve checkpoint provisioning/loading.

After the separate exact artifact/compute decision, a trusted operator can
inject the deployment configuration at process launch:

```sh
agent-braid forecast predict owned-request.json --cpu-manifest private-manifest.json
agent-braid forecast serve-mcp --cpu-manifest private-manifest.json
```

The owner record must be an owned, no-follow regular file with mode `0600`, a
SHA256 pinned in the separately installed private deployment registry, unexpired exact manifest binding and the
scope `local-cpu-synthetic-conformance`. The fixed registry is `~/.config/agent-braid/forecast/owner-approval-pins.json`,
installed separately by the owner deployment process after retaining the actual
decision. A caller-generated self-hash cannot populate this trust anchor. Neither
launch arguments, numeric requests nor MCP tools can select a pin or registry.
Both registry and retained record are re-read on every verification; removal,
mutation or expiry revokes the artifact. Deployment validation is lazy with respect to model loading.
The Python API accepts an independently injected verifier directly. Revocation
refuses forecasts, clears reuse and closes the owned worker.

The worker verifies a local Unix Docker socket, immutable image, owned checkpoint
hashes, applied configuration and effective cgroup v2 limits before loading.
Profile: total container memory 2 GiB, memory+swap 2 GiB (zero swap), CPU quota 1,
one library thread, 64 PIDs, 64 MiB scratch, read-only root/model mount, nonroot
user, dropped capabilities, no privilege escalation and no network. Context is
128 bins; horizons are 1/5/10. Cold admission/loading has a 30-second budget;
resident requests have a one-second budget. Failed limits are refusals; no limit
is automatically increased. Peak process RSS and current container memory have
different scopes. Model CPU time is measured separately.

## Cleanup and diagnostics

A private cross-process lease permits one resident worker. Failed cleanup or an
uncertain Docker create keeps a persistent blocking marker. Recovery must inspect
the marker's exact owner/manifest and the container name
`agent-braid-forecast-OWNER`, verify both ownership labels, remove only that owned
container, confirm absence and then record cleanup before clearing the marker.
Never delete a lease while its holder is alive or run host-wide cleanup. The
current automatic path deliberately fails closed when the engine cannot confirm
cleanup; this recovery remains an operator procedure. A blocked client stdout
can also require process supervision; an unconfirmed lease must be preserved.

Cache keys include the full request, causal/source/resource/partition/transform
identities and model manifest. A hit reports its current work and retains the
original receipt identity separately. Baseline intervals are heuristic and carry
`not-evaluated` calibration. Shadow retains the reference action; synthetic drift
monitoring can rehearse sticky rollback to off. Permissioned runtime advice and
the System 1 bridge remain unavailable pending accepted source/consumer chains.

## Reproduction and limits

Run `scripts/reproduce_forecast.py` with the installed environment's Python from
outside the checkout. It exercises all eight seeded families, three partitions,
three horizons, both cheap baselines, absent-model refusals, CLI/MCP parity and
optional independently granted paired Git controls. The actual CPU driver is
`scripts/reproduce_forecast_cpu.py`; it requires the separate retained approval.
It keeps all attempted outcomes, two warmups and five measured cycles, cold and
resident costs, multivariate/covariate shape probes, preflight cancellation and an
active-request cancellation attempt with owned cleanup. It reports whether
cancellation was actually observed while active; physical in-kernel interruption
is not inferred. OOM/engine-crash controls and
model clean-room reproduction are explicitly separate pending procedures.

The synthetic policy cost model uses fixture constants, not observed real
policy timings. Arm wall time includes data preparation through arm cleanup;
episode wall additionally includes owned session cleanup and coordinator
residual. Export/provisioning and external resident lifecycle are separate
boundaries and must be added before claiming complete deployment cost. Raw cost
ratios and forecast accuracy never accept real workload utility or promotion.
