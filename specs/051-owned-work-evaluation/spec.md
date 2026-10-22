# SPEC-051 — Pure owned-work authority and evaluation contracts

Status: adopted for bounded local implementation, 2026-10-21. Founder instruction:
“Adelante, adopta SPEC-051 e implementa los módulos puros de autoridad y validación
RF-T01/RF-T02 en el M3 Pro, sin gasto externo. Mantén el relevo documental y deja
pendientes captura real, entrenamiento, revisión humana y activación.” This is
scope authority for software work, not completed human/scientific review or source
consent. Public integration remains subject to Governance review and PR.

## Scope and lineage

RF-T01 = original proposed SPEC-045/T009, REQ-CI-001 / SC-CI-001;
RF-T02 = SPEC-045/T010, REQ-CI-002 / SC-CI-002. This separate feature implements
those two planning aliases without changing historical SPEC-045 task dispositions,
synthetic source contracts, SPEC-047 aggregates or typed-v1 domains. Baseline:
`a6329c828011d1468fed3dfa4e98f5a8531167e2`. Adopt RF-DEC-001 (separate scope) and
RF-DEC-002 (late outcomes preserve the original horizon's censoring).

## Requirements

- **REQ-001 / SC-001 — RF-T01:** exact bounded authority descriptor plus a trusted
  operator-owned snapshot resolves immutable validation context or precise refusal.
  Missing registry, callable stubs, mismatched root/scope/pins, expiry/revocation,
  inadmissible actions and caps refuse. JSON flags/digests never mint consent.
- **REQ-002 / SC-002 — RF-T02:** bounded raw JSON admission and exact structural
  schema followed by immutable state validation: chain/identity/origin/correction,
  T0 availability, source/method/oracle bindings, family partitions, same-clock
  times, units, unknowns, spans and right censoring. Reject duplicates, nonfinite
  values, bool integers, unsupported fields/versions and diagnostic content.
- **REQ-003 / SC-003 — Compatibility:** stdlib only; no I/O, store, observer,
  subprocess, model, collector, CLI or MCP registration. All execution/training
  authority remains false. Tests measure software controls, not forecasting skill.

## Trust and scientific boundary

The host supplies a fresh immutable trusted registry snapshot from an operator
path outside model wire input. Its constructor is a Python-code trust boundary,
not secure storage, signature verification or hostile same-UID protection. The
pure resolver compares descriptor bytes and approved receipt references; it cannot
establish the truth of caller-provided consent, canonical filesystem root or
artifact provenance. Physical root/link/ownership verification and secure registry
write/read/revocation are prerequisites for RF-T03 and real capture, not delivered
here. No permissive verifier callback or wire registry adapter is supplied.

A separate frozen registration declares every attempted member and its family,
source/config/toolchain/clock/oracle/method and prospective evidence. Unregistered
attempts refuse. A coverage report preserves absent origins/outcomes as missing;
it is not proof that the supplied population is complete. Validation accepts
synthetic test fixtures only in this lot; a parseable record is not source admission.
Human and semantic labels remain unknown. Negative old native utility is unchanged.

## Non-goals and stopping

RF-T03 persistence, RF-T04 observation, RF-T05 real oracle/population admission,
forecasting/model execution, real capture, training/calibration, human/scientific
review, promotion, host/global activation, release and remote publication remain
pending. No independent review of this new code is claimed. Stop only the affected
route on invalid authority, state or budget; do not mutate product output/grants.
