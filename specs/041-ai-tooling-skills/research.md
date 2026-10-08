# SPEC-041: Research and decisions

Retrieved 2026-10-08. The authoritative shared [research register](../039-ai-tooling-program/research.md) records selected versions, sources and alternatives.

## Local design decision

Canonical product skills live in integrations/agent-braid/skills, separately from generated Spec Kit adapters. Minimal host metadata supplies discovery; instructions describe workflow and refusal paths without hooks or grant creation.

## Why and alternatives

A shared typed core reduces duplicated host semantics; CLI remains the reproducible baseline. Skills-only wrappers lose standardized discovery; host-only implementations risk divergence. Hosted services and embedded UI expand the surface and are future routes.

## Evidence needed

Focused portable guidance may improve workflow completion and evidence fidelity; model compliance and positive utility are not presumed.

Verify each proposed feature under the named validation procedures. Vendor documentation is source material, not host runtime evidence. Source rights, numeric budgets, exact versions and candidate review precede registered capture.
