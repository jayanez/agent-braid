# SPEC-067: Validation plan

Procedures are planned, not run. Unit procedures prove logic with fixtures and
goldens; they do not prove review quality or any outcome benefit.

Commands use the isolated environment: `.venv-speckit/bin/python -m unittest …`.

| Procedure | Scenario | Test target | Expected | Negative controls |
|---|---|---|---|---|
| procedure_001 | SC-001 | `tests/test_harness_assurance.py` | full profile compiles with per-checkpoint view | unknown/missing checkpoint, unknown depth, disallowed mode, unknown key |
| procedure_002 | SC-002 | `tests/test_harness_assurance_receipts.py` | in-scope valid authorization cited in receipt | missing, expired, revoked, out-of-scope, issuer not permitted, mode not admitted, missing verbatim statement, failing condition: all fall back to `approve-each` |
| procedure_003 | SC-003 | `tests/test_harness_assurance.py` | floors hold; lowering refused and recorded | conversation/repository/user lowering of each floor; each floor checkpoint not `human-only`; attribution invariant disabled |
| procedure_004 | SC-004 | `tests/test_harness_assurance_risk.py` | raise-only; deterministic bytes | rule below configured depth or mode; docs-only class reported; same diff twice differs |
| procedure_005 | SC-005 | `tests/test_harness_assurance_receipts.py` | R0–R4 required-review sets enforced | missing review, lower depth than required, other head commit |
| procedure_006 | SC-006 | `tests/test_harness_assurance_render.py` | byte-identical artifact, brief and PR section | `executionAuthorization: true`, digest mismatch |
| procedure_007 | SC-007 | `tests/test_harness_assurance_receipts.py` | valid receipt verifies | edit without digest recompute, wrong commit, profile digest mismatch, depth below effective, command without exit code |
| procedure_008 | SC-008 | `tests/test_harness_assurance.py` | agent-origin change refused; human promotion versions and restores | agent-writable source, agent identity, in-place edit of a journaled version |
| procedure_009 | SC-009 | `evidence/t009.json` review | outcomes, arms, stop rules fixed before data | benefit claim without record; post-hoc outcome change |
| procedure_010 | SC-010 | existing suite + `validate_change` | results equal pre-change | any changed existing result |

Repository validation for every change: `quick` after an increment and `pr` on
the stable candidate, through a clean clone while the shared object store fails
the portable-root check.
