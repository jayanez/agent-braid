# SPEC-040: Research and decisions

Retrieved 2026-10-08. The authoritative shared [research register](../039-ai-tooling-program/research.md) records selected versions, sources and alternatives.

## Local design decision

Introduce a new SDK adapter around existing RuntimeTools and analyzers. Preserve legacy six tool names and entry point, add analyze-work, version the output envelope, advertise only configured capabilities and bind every root at startup. Resources/prompts expose bounded evidence/guidance.

## Why and alternatives

A shared typed core reduces duplicated host semantics; CLI remains the reproducible baseline. Skills-only wrappers lose standardized discovery; host-only implementations risk divergence. Hosted services and embedded UI expand the surface and are future routes.

## Evidence needed

A standard typed interface may improve discovery and interoperability; SDK conformance alone does not prove real-host support or semantic correctness.

Verify each proposed feature under the named validation procedures. Vendor documentation is source material, not host runtime evidence. Source rights, numeric budgets, exact versions and candidate review precede registered capture.
