# SPEC-042: Research and decisions

Retrieved 2026-10-08. The authoritative shared [research register](../039-ai-tooling-program/research.md) records selected versions, sources and alternatives.

## Local design decision

Package installed resources and optional SDK extra. Implement tooling serve/configure/install/doctor/update/uninstall with previews, scoped apply and ownership receipts. Use actual per-host scope semantics, conservative edits and refusal on collision/drift.

## Why and alternatives

A shared typed core reduces duplicated host semantics; CLI remains the reproducible baseline. Skills-only wrappers lose standardized discovery; host-only implementations risk divergence. Hosted services and embedded UI expand the surface and are future routes.

## Evidence needed

Predictable installation and diagnosis may lower adoption effort; reusable installation does not imply universal repository access.

Verify each proposed feature under the named validation procedures. Vendor documentation is source material, not host runtime evidence. Source rights, numeric budgets, exact versions and candidate review precede registered capture.
