# SPEC-086 owner decisions (2026-11-26)

Refinement of the specification structure under the "Specification conventions" of `docs/development/SPEC_KIT.md`. Asked interactively; the owner chose the recommended option in every question.

| Decision | Answer | Meaning |
|---|---|---|
| Exclusions without a requirement | "REQs nuevos 012 y 013 (Recomendado)" | REQ-012 (no host exporter configuration and no host OTLP ingest) and REQ-013 (`execution_authorization` false on every span and result) with scenarios SC-013 and SC-014 in `assurance.json`. |
| Loopback-only export | "REQ-014 loopback (Recomendado)" | REQ-014: export only to loopback (OD-5), no redirects, bounded body, with scenario SC-015. REQ-006 is unchanged. |
| Spans, dashboards and scores as promotion or grant | "REQ-015 nuevo (Recomendado)" | REQ-015: no command turns a span, dashboard or score into a promotion or grant, with scenario SC-016. |
| Offline derivation (no hot-path code) | "Citar OD-2/T006, sin REQ (Recomendado)" | Stated in the non-functional requirements with its sources OD-2, plan and T006; no new requirement. |

REQ-001 to REQ-011 are unchanged. The earlier decisions OD-1 to OD-8 remain as recorded in `t001-owner-review.md`. Open questions left: OD-8 release alpha and the REQ-009 overhead limit. No scientific claim changes; `executionAuthorization` stays false.
