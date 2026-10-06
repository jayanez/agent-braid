# Capability refinement matrix

Draft engineering assessment. Existing accepted scope is private fixed-patch Git
execution under ADR 0019 and SPEC-020. SPEC-021 whole-M4 utility remains NO-GO.

| Capability | Current evidence | Missing premises | Supported fallback |
|---|---|---|---|
| Source-ref promotion | Read-only tree/result identity and Git target observations | Independently verified result; promotion-specific grant; exclusive revalidation/CAS; ownership; crash reconciliation; adopted contract | Export result and manually reviewed integration |
| Project-code checks | Executable-presence inventory only | Enforced credential, filesystem, network, descendant and memory controls; immutable checkout; reviewed harmless probes and exact authority | Read-only analysis/private patch replay |
| External writes | Abstract per-attempt events and failure outcomes | Specific provider/rights, idempotency semantics, visible observation, partial-failure recovery, adapter refinement and operation-specific grant | Offline simulation; abstain on ambiguous success |

`check_runtime_refinement.py` reports proposals or refusal, never consumer
verification, runtime acceptance or execution permission. A supplied object ID is
an identity, not evidence of successful independent verification. Installed command
presence supplies no isolation guarantee. No sandbox or project command is launched.
