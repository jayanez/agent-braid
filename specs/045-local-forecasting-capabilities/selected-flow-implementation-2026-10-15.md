# Selected full-flow measurement implementation

This is the C1–C4 engineering increment of the
[reviewed T007 plan](https://github.com/jayanez/agent-braid/issues/517#issuecomment-6193983777).
It performs no VM/model execution and closes no task. Original criteria and
historical assurance remain unchanged.

## Reuse and new obligations

| Existing obtained component | Reuse / new work |
|---|---|
| Admitted integrated worker/daemon fault | Preserve obtained outcome, exact artifacts, lifetime counters and limits; do not rerun the fault or empty-daemon qualification. |
| CostRecorder v1 and its publication observer | Reuse stage/interval/gap validation. Preserve the final-attestation gap rather than adding another recursive supervisor. |
| ForecastSession and its cache | Use the existing session in the own guest; count actual worker invocations H1/H5 and check the third H1 session request is a cache hit. |
| Paired Git fixture harness and external grants | Reuse all six arms over independent/dependency fixtures and deterministic tree verification; consume this operation's fresh H1, with shared model acquisition cost outside arm timing. |
| Separate earlier model and Git episodes | Retain them as historical evidence; never splice them into a new measured episode. |
| New boundary and collector-to-consumer wiring | Add `forecast_fullflow`, the simulation-only driver and the [v2 boundary](contracts/selected-operation-cost-v2.md). A new private collector package requires exact review and owner admission. |

The selected operation now has a finite stop: owned cleanup plus durable product
payload write/readback. Its final metrology attestation is explicitly outside.
V1 receipts keep their original `publicationIncluded=false`; full deployment and
economic acceptance remain false. This resolves the engineering measurement
contract without silently weakening the literal complete-cost task criterion.
Historical acquisition/build CPU, unavailable host-service/bootstrap counters,
and final-attestation costs are still gaps. A new run cannot recover old costs.

## Controls and execution boundary

The new controls distinguish a healthy six-arm flow from altered nonce/window,
extra model calls, false cache, invalid grants, interrupted collection and failed
export. The standalone CLI only simulates model packets and has no VM, Docker,
model-path or arbitrary-command option. For a real run the private procedure
must bind every collector/native/guest/host-wheel byte and reserve the existing
forecast profile. No decision/pin is installed during preparation.

Actual measurement C5 and evidence-based acceptance C6 are pending. A reviewed
package may measure the selected batch once, under exact limits; it does not
promise T007 closure, independently admit FC.1 sources or establish utility.
Stop after a failed admitted attempt and retain its partial records. No automatic
next package, retry, extra fault, download or limit increase.
