<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# M4.5 session coordination boundary

`agent_braid.tooling_sessions.execute_admitted_attempt` coordinates one
previously admitted slot. It does not implement a Codex/Claude host adapter,
provider client, MCP connection, grant operation, or human decision. Real
adapters are implemented separately in [HOSTS.md](HOSTS.md); an authenticating
`OutcomeVerifier` remains an external trusted-caller requirement.

The coordinator reopens the admission receipt from the fixed per-user store and
checks its exact hash, registration, slot, attempt ID, fixture identity,
candidate, and candidate artifact. A registration-wide exclusive reservation
serializes dispatch across all 108 slots. Its persisted head must equal the
exact supplied ledger hash before a slot can start; after a verified outcome,
the head advances atomically to the new ledger hash and is fsynced. Thus two
different admissions prepared from the same old ledger cannot both dispatch:
the second is refused while the first is active and remains stale after the
first completes. The admission receipt itself is never rewritten.

The reservation is written before the per-slot started marker and before
adapter dispatch. If the process crashes or verification fails, the reservation
remains active and blocks the whole registration pending inspection. The
coordinator does not clear it or permit another baseline to proceed
automatically. Operators must preserve the evidence and resolve this boundary
through the separately governed recovery procedure; this module has no
resume/replay operation.

After reserving the head, every dispatch must also supply fresh cumulative
`MeasuredCosts` and `StopState` observations plus a typed `StartAttestation`
from the injected verifier. The attested subject binds the registration, slot,
admission receipt, exact ledger head, cost provenance and values, stop-state
provenance and values, and the minimum timestamp floor. The observations must
be at least as recent as the admission and ledger events; costs cannot regress
from the admission snapshot, omit a previously known field, exceed registered
caps, or conflict with prior-slot totals. Open incidents, unrecoverable runs,
and two consecutive infrastructure failures refuse dispatch. Failed preflight
verification releases the reservation without writing a started marker, so
the slot remains unstarted. The coordinator does not authenticate observations
itself; that remains the trusted verifier's job.

The injected adapter performs at most the single call made by the coordinator.
The injected verifier receives the exact admission, slot, raw adapter response
and a canonical subject hash that binds them. It must return a typed normalized
outcome and an attestation for that exact subject. The coordinator rejects
unbound attestations, input-hash mismatches, malformed outputs, and malformed
cost records. It records verified null costs as null; it never substitutes zero.
An accepted outcome is appended to the immutable evaluation ledger and sealed
in a separate sibling receipt.

If adapter dispatch, candidate drift checks, or outcome verification fail after
the durable start, the coordinator writes a separate interrupted record with a
bounded failure class and explicit null costs. The attempted ledger event stays
open. A later inspection can recover that attempted event from the exact
pre-start ledger snapshot, but it cannot dispatch or synthesize a terminal
outcome. A started marker without a sealed result is `started-unknown`; never
retry it. Keep the original raw adapter receipt and any external diagnostic
records in their controlled evidence store; this module retains only hashes
and verifier-normalized outcome fields.

`inspect_session` is read-only. `reconcile_started_ledger` only restores the
durably recorded attempted event when the supplied ledger matches the exact
pre-start hash and registration roster. Neither operation authenticates a
provider, owner, source right, grant, human rating, or adapter. Only the
configured trusted verifier may attest to those inputs and observed outputs;
the test verifier is synthetic and is not an authority.

The coordinator checks the registered cumulative cost caps both at admission
and immediately before dispatch using the required fresh observation. It
combines that cumulative baseline with verified per-attempt costs once, while
prior-slot totals are validated against the ledger without being added twice.
It can validate verified final costs and preserve unknowns, but it does not
claim a hard live kill. The [process supervisor](SUPERVISOR.md) composes with
[host adapters](HOSTS.md) and fresh externally verified cumulative telemetry
for local process-group stopping. Its controls use owned synthetic processes.
Sampled telemetry and local cancellation do not establish a provider spending
ceiling or prove that an external operation stopped. Actual verified capture
remains pending; these components do not satisfy W18/W19 by themselves.
