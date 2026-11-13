# Owner decisions, 2026-11-13 (SPEC-050 remaining scope)

Recorded from interactive owner answers (guided questions with options, risks and undo
paths). The orchestrator relayed each answer as the chosen option label; the decisions
below restate the chosen option. These records authorize no native execution, adopt no ADR
and activate nothing.

Context: SPEC-050 has no offline work left after T011 (#1317), T012 (#1324) and the
THIRD_PARTY.md provenance entry (#1326). The host was updated to macOS 27.2.1, build
26B131. The SPEC-065 qualification was issued for build 26B123 and requires
requalification on a build change, so it no longer covers this host. It would also have
expired on 2026-12-06T18:07:44Z.

| # | Topic | Decision | Effect |
|---|---|---|---|
| D1 | Pending endpoints (T009, SPEC-049/T008 rule 12) | Tolerate none for now. | The production policy stays unchanged and abstains with `pending-endpoints`. Revisit when SPEC-049/T014 measures the endpoints. |
| D2 | Native chain | A dedicated HAR wave after 2026-12-06. | One SPEC-065 requalification on the current build, then SPEC-048/T008, then SPEC-049/T004, then SPEC-049/T014. Subscription only, no paid route, EUR 0. Nothing native runs before that wave. |
| D3 | T010 top-level alias | No alias; close T010. | Access stays `python -m agent_braid.harness_advisory`. Plugin/MCP exposure, if wanted, belongs to milestone M4.8 under its own versioned contract. `tests/test_harness_cli.py` and the SPEC-049 evidence stay untouched. |
| D4 | Lifecycle retention (T011) | 30 days. | Callers of `harness_lifecycle.retain` pass an expiry 30 days after retention starts. A human purge afterwards deletes the records and keeps the digest receipt. This matches the S1.5b Q5 pool. |
| D5 | Independent review | Luna now, over the merged offline portfolio. | Packet: [review/luna-packet-20261113.md](review/luna-packet-20261113.md). The owner runs it outside this host, because no Luna client is installed here. Findings are recorded under `evidence/review/` and fixed before the native wave. A delta review follows the native evidence. |
| D6 | Human usability observation (T011) | After the native wave. | Observe it on a real qualified profile. It stays pending until then. |
| D7 | Activation policy, ADR and operator decision | When SPEC-049/T014 has results. | No ADR or policy is drafted now. A positive T014 leads to a Proposed ADR with measured criteria. A negative or inconclusive T014 closes the harness as experimental. |

Remaining SPEC-050 status after these decisions:

- T010 is ticked under D3.
- T004 stays partial. Its subprocess/network adapters need SPEC-048/T008 and an adopted E3
  effect contract (D2).
- T012 stays partial. It waits on the D5 review record, the D2 native evidence and the D6
  observation.

## Amendment, 2026-11-13 (later the same day)

The owner changed **D2** to start the native HAR wave now: "Sí, empezar ya". The
reason for waiting no longer held. The SPEC-065 qualification was already void on build
26B131, and a new one lasts 30 days from issuance. The order is unchanged: SPEC-065
requalification, then SPEC-048/T008, SPEC-049/T004 and SPEC-049/T014. Everything uses
the subscription, with no paid route and EUR 0.

Pre-check on 2026-11-13 found no change that needs new code or a security re-check:

- The hashes of `/usr/bin/sandbox-exec`, the pinned `claude-2.1.292` and the lab
  `python3.12` are unchanged.
- The containment, probe, transport and attempt-script sources are identical between the
  qualified commit `320b00c4` and `develop`.

Requalification attempt `t009-20261113a` therefore reuses commit `320b00c4`, and only the
environment changes. Nothing native has run yet. Each real attempt still needs the
orchestrator's check verification and the owner's own run.

Status, 2026-11-13: the SPEC-065 requalification is issued (T013, attempt `t009-20261113c`, headless
mode at `7d3e1986`; record `specs/065-native-claude-containment/evidence/qualification/issuance-2026-11-13.json`,
valid until 2026-12-13T16:14:45Z); SPEC-048/T008 is next.
