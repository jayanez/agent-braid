# Synthetic software technical review

Reviewer: Luna Latest (`gpt-6-luna`), separate context
`/root/forecast_boundary_review`. Date: 2026-10-14. This is a technical source
review and focused independent verification, not an owner/founder approval.

Disposition: no remaining blocker to the default-off synthetic software
candidate. The reviewer independently executed `tests.test_forecast_worker`:
seven tests passed, including bounded stdout/stderr and timed cancellation.
Whole-repository validation remains a separate executed procedure.

Reviewed fixes include causal availability/future covariate identity and units,
complete cache bindings, synthetic-versus-runtime provenance, malformed output
cleanup, shared admission/uncertain-create lease, applied mounts and effective
container profile, bounded Docker control subprocesses, live owner-registry
revocation, MCP ID/cancellation/failed-request lifecycle, schema-bound immutable
receipts, frozen synthetic partitions/labels and explicit fallback denominators.

Inspected final hashes:

| File | SHA256 |
|---|---|
| `agent_braid/forecast_worker.py` | `084675131ad3bbcf4a6e140055262c1d7b460f17bea14bf0d91307ed8a4692a2` |
| `scripts/reproduce_forecast_cpu.py` | `6397d79c454356137a674671ca80e0fe17082241bd53b9ec0c0cf3898e6f53bf` |
| `specs/045-local-forecasting-capabilities/issue-drafts.json` | `551f164915743e81d0ce112b19cba82e2a4f8beca3a9d36396aa6a5a253ed4e9` |
| `docs/forecast/OPERATIONS.md` | `9a1ce81fb35a0078cdd34ebfa1ac27173acf6cf94415110994578c44e7821a8b` |

The deployment registry is a same-UID local-owner filesystem trust anchor.
Requests cannot inject its pins; another process running as that owner can
replace it. It is not cryptographic proof that a human decision occurred.
Only an actual retained owner decision may be installed by the trusted
deployment process. Actual artifact/load/conformance, source/launch/scientific
interpretation/promotion and feature human acceptance remain pending.

Earlier OOM control timed out and remains recorded as incomplete evidence. A
corrected chunk-allocation control subsequently observed cgroup OOM exit137,
effective limits and owned process exit17 with confirmed cleanup. This separate
measurement uses synthetic processes and does not load Chronos.

## CPU lifecycle and diagnostic delta

On 2026-10-14 the same independent reviewer (`gpt-6-luna`) inspected the
stdin/TTY applied configuration, OOM/exit diagnostics retained before removal,
and the 270-second request budget within the 300-second total budget. The
reviewer executed the worker and CPU procedure suites: nine tests passed.
The subsequent completeness finding concerned omitted diagnostics in the
shape and cancellation attempt rows. It was corrected, including the preflight
cancel row, and the reviewer independently executed
`.venv-speckit/bin/python -m unittest tests.test_forecast_cpu_procedure -v`:
two tests passed. No remaining defect was found in that delta.

| Reviewed file | SHA256 |
|---|---|
| `agent_braid/forecast_worker.py` | `948d400290f0ce03afbe592288c1c02367a7bfcba80f60d72f16177aa979c429` |
| `scripts/reproduce_forecast_cpu.py` | `a0761c1ab2e396fdd31c4871453b09caa6b4e16b9263cc4bb76c5242bb85890a` |
| `tests/test_forecast_cpu_procedure.py` | `9c4708df79cdcde451edbaa3a9a5a73d370d777c0428d317bb9e8ad34765b86f` |
| `docs/forecast/OPERATIONS.md` | `1676d5b8fe33a58e2bea63f37971fc94869de84af1b1803ccd45b9c9be36f45e` |

The regression uses a synthetic worker that clears its diagnostics during
cleanup. It verifies OOM/exit137 retention on a failed shape probe and all 173
rows on the complete cancellation path. This is software evidence. The real
pinned-image ready probe sent no load command, and no Chronos model has been
approved or loaded. Earlier hashes above retain their historical review scope.

Original task closure candidates remain SPEC-034/T002 and T004, subject to
their task-specific receipts and stable repository checks. Other original
criteria and predecessor gates remain pending; technical review does not waive
them or accept a real source, model budget, experimental launch or promotion.
