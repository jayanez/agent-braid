# ADR 0026: Pure owned-work validation boundary

Status: adopted for local software design by explicit owner instruction on
2026-10-21; public integration/review and actual source admission pending.
Articles: 0, 5, 7, 12–14, 19–20, 23–25.

Separate SPEC-051 from SPEC-045 synthetic forecasting and SPEC-047 numeric
telemetry. Implement only immutable authority snapshot comparison and pure
cross-record validation. Reject wire-provided or callback-created authority.
The caller's operator-controlled Python snapshot is the trust root; this design
cannot authenticate arbitrary same-process code or discover filesystem facts.
Do not ship a registry loader, source observer or store in RF-T01/RF-T02.

A hash identifies bytes, not consent or proof. No actual admission follows from
this architecture. A future secure registry/storage boundary must verify canonical
roots, rights, consent, review, freshness/revocation and artifact content before
creating trusted snapshots. Late completion retains right censoring against the
original forecast horizon. Existing synthetic and collector contracts do not change.

Alternative: relabel synthetic recorder as real work. Rejected because its source
and privacy contracts differ. Reusing numeric causal-window contracts remains a
future adapter task after actual source admission. Tests are engineering evidence,
not scientific validity or semantic gold. See SPEC-051 spec, migration and contract.
