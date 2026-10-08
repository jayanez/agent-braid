# Implemented assessment verification

The read-only assessment CLI and synthetic controls are implemented. No expanded operation is authorized by this assessment. The founder has recorded
NO-GO/defer dispositions for source promotion, arbitrary code execution and real
external effects by the bounded M4 alpha runtime. Those decisions preserve ordinary
authorized project delivery/testing and do not adopt capabilities or issue grants.
See the [derived decision record](evidence/founder-capability-dispositions-20261008.json).
See `evidence.json` and `tasks.md` for the candidate-bound obtained evidence;
assessment completion alone did not close T007; its three bounded-M4-alpha disposition decisions are now recorded. This does not close M4.

## SC-001 — Separate grant scope

`tests/test_runtime_refinement.py` rejects current private-runtime grants as
promotion/code/external authority. It checks unknown capabilities, unsupported
fields and missing object premises without executing expanded operations.

## SC-002 — Promotion dry-run

The controls use owned disposable Git fixtures with expected refs,
detached/attached worktrees, dirty indexes and stale bases. The implemented CLI
accepts a bounded assessment input and a fresh output:

```sh
python3 scripts/check_runtime_refinement.py --capability promotion --input /absolute/fixture.json --output /absolute/fresh/assessment.json
```

Its result is `proposal-only` or `refused`, with `sourcePromotion:false` and
`executionAuthorization:false`. Source immutability controls and simulated fault
classifications are implemented. Independent result consumption, exclusive
revalidation/CAS and actual ref publication remain future capabilities.

## SC-003 — Code isolation feasibility

Read-only executable-presence inventory is implemented:

```sh
python3 scripts/check_runtime_refinement.py --capability code-check
```

Presence does not establish enforcement. The inventory reports `NO-GO`,
`enforcement:not-verified`, zero executed probes and the unsupported filesystem,
network, descendant, memory and credential controls. Review exact harmless
synthetic probes and obtain their execution authority before running them. Do
not run project code or install a backend through this assessment.

## SC-004 — External-effect failure model

The implemented simulator retains immutable in-memory synthetic attempts and
visible events for retries, duplicate delivery, ambiguous timeout and
failure-after-emission:

```sh
python3 scripts/check_runtime_refinement.py --capability external --input /absolute/attempts.json --output /absolute/fresh/assessment.json
```

It makes no provider call. Uncertainty remains unresolved; automatic retry and
execution authorization remain false, and compensation is not claimed to be an
inverse.

## SC-005 — Decision and gates

The existing assessment module contains nine controls:

```sh
python3 -m unittest tests.test_runtime_refinement
```

Inspect each packet's capability scope, prerequisites, evidence, restrictions,
fallback and decision scope. The frozen `capability-disposition-packet.md` remains
the recommendation presented to the founder; its pending language is superseded by
the derived decision record, which records three NO-GO/defer dispositions for bounded
M4 alpha only. No capability was adopted into M4 or a future implementation track.
Repository quick/PR profiles validate executable checks and artifacts, not ADR
adoption, source permission, expanded execution or whole-M4 acceptance. Historical
candidate-bound review and evidence records retain their original observations.
