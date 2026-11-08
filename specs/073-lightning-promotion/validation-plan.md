# SPEC-073: Validation plan

Status (draft): no procedure has obtained evidence. Deterministic procedures
run with `.venv-speckit/bin/python -m unittest` on targeted modules, against
temporary plugin homes and a copied plugin tree.

| Procedure | Scenario | Test target | Expected | Negative controls |
|---|---|---|---|---|
| procedure_001 | SC-001 | `tests/test_lightning_promote.py` (planned) | valid native record from a winner with H1 `supported` and the SPEC-049 pair | unknown scope; digest mismatch; oversize text; H1 not supported → `no-held-out-support` without override reason |
| procedure_002 | SC-002 | same, apply tests | human approved → begin → commit journaled | automatic actor refused; synthetic cohort refused; stale identity refused |
| procedure_003 | SC-003 | CLI preview tests | preview printed, no bytes changed; apply only with matching digest | registry or file changed after preview → `preview-stale` |
| procedure_004 | SC-004 | build check tests | build passes when file digest equals active | edited file → mismatch names scope and both digests |
| procedure_005 | SC-005 | rollback tests | previous digest and text restored; build passes | rollback with no previous → `no-previous` |
| procedure_006 | SC-006 | revocation tests | cited evidence revoked → previous candidate active | uncited evidence revoked → no change |
| procedure_007 | SC-007 | reflection tests | entries quarantined | 513-character text refused; poison pattern refused |
| procedure_008 | SC-008 | boundary tests | no socket, subprocess or non-stdlib import; writes only to allowed paths | patched module opening a socket fails the test |
| procedure_009 | supplementary (no scenario), owner run under T010; supports SC-002, SC-004, SC-005 | owner-run script `scripts/spec073_owner_promotion.py` (planned) | recorded decision, rebuilt plugin digest, rollback digest | none (real-use evidence) |
