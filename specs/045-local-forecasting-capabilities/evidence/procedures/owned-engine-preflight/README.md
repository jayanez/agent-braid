# Owned-engine preflight failure receipt

This pure local protocol fixture addresses the v7 observation where `/info`
returned JSON `null` and `/images/json` returned HTTP 499. The native preflight
correctly withheld the crash token, but the VM supervisor also stopped the VM
immediately. That prevented the guest's existing bounded EXIT trap from
retaining the daemon log and a completion marker.

The protocol now models rejection separately from VM shutdown: rejection emits
no token and allows a five-second receipt grace; a completed guest receipt stops
the VM, while a missing receipt stops it after the deadline and remains
incomplete. Cancellation is terminal: queued readiness cannot admit a token
after a stop request. Token delivery is serialized with signal handling on the
main event queue, and a failed bounded write transitions to the receipt path.
Successful preflight admits one token only. Diagnostic parsing
reports bounded HTTP status/top-level-null observations with `engineReady`,
`ownedDaemonCrash`, and `executionAuthorization` fixed false.

Run the synthetic native parser/admission tests from the repository root:

```sh
swiftc \
  specs/045-local-forecasting-capabilities/evidence/procedures/owned-engine-preflight/engine_preflight.swift \
  specs/045-local-forecasting-capabilities/evidence/procedures/owned-engine-preflight/admission_gate.swift \
  specs/045-local-forecasting-capabilities/evidence/procedures/owned-engine-preflight/tests/main.swift \
  -o /tmp/fc2-owned-engine-preflight-tests
/tmp/fc2-owned-engine-preflight-tests
```

The fixture does not create a VM, open a socket, run Docker, send a token, or
exercise guest EXIT-trap timing. It verifies parser outcomes and supervisor
state transitions independently. A future exact execution procedure must bind
these source digests, connect the gate to its supervisor, and test cleanup and
guest receipt delivery under its own review and owner decision. This evidence
does not qualify the worker, establish costs or utility, or authorize another
execution.
