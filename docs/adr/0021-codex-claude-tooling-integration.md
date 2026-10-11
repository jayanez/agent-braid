# ADR 0021: Portable tooling integration for Codex and Claude Code

- **Status:** Proposed; the owner approved preparation of the M4.5 program on
  2026-10-08. This is not a recorded adoption of this ADR or milestone closure.
- **Date:** 2026-10-08
- **Constitutional articles:** 0, 3–7, 12–16, 19–25
- **Program:** [SPEC-039](../../specs/039-ai-tooling-program/program.md)

## Context

M1/M2 provide analysis and replay. ADRs 0019/0020 admit bounded private Git
execution, grants, recovery and a local MCP adapter. Product adoption needs
discoverable capabilities, installation, host-specific observations and an
evidence-oriented workflow. The existing adapter and historical host observations
do not establish the proposed product's compatibility or utility.

## Proposed decision

Create adjacent milestone M4.5 with SPEC-039–044. Support Codex and Claude Code
first. Build a shared stdio MCP surface with the official Python SDK in an
optional extra, initially pinned to `mcp==2.3.0`. Keep core dependencies empty.
Select protocol 2026-07-28 with tested 2025-11-25 compatibility. Delegate all
execution, recovery and verification to the existing runtime and grant policy.
Keep existing names and result semantics available during migration.

Ship five portable Agent Skills plus minimal host packaging metadata. Maintain
product skills outside generated Spec Kit adapters. Provide reproducible package
assets, explicit global or project installation, configuration previews,
diagnostics, safe updates and removal. A reusable user package does not imply
access to every repository: each configured server has explicit trusted roots.

Default to analysis; runtime activation is an explicit operator configuration.
Grant issuance is never a model-callable MCP tool, prompt, resource or skill
script. Existing grants remain bound to their exact candidate/policy/run scope.
Host tool permission and runtime authority are separate checks. No arbitrary
repository command, source promotion, network adapter or new effect is admitted.

Expose compact, typed results and bounded resources/prompts. Explain conflicts,
unknowns, evidence and recovery in chat and in deterministic offline exports.
Assess CLI, MCP-only and MCP-plus-skills workflows on the same registered inputs.
Actual host observations, protocol controls, clean reproduction, human review
and founder closure remain separate records.

## Alternatives

1. Extend the handwritten SPEC-021 server indefinitely: fewer dependencies, but
   transport and version maintenance remain project responsibilities.
2. Separate implementations per host: convenient customization but duplicated
   semantics and authorization checks.
3. A hosted service or embedded MCP App: broader presentation and authentication
   surface; requires separate contracts and is deferred.
4. Only skills wrapping CLI: useful fallback, but loses standardized discovery
   and structured host results. Retain CLI parity as a baseline.

## Compatibility and consequences

No existing AIM, certificate, runtime, grant or historical evidence is rewritten.
SDK transitive dependencies need license/provenance review and isolated installs.
New public envelopes receive an additive experimental version and migration note;
tool annotations remain descriptive. Support is bounded by recorded host versions,
OS and transport, never an assertion about every version or cloud executor.

Public documentation remains English, documentation CC-BY-SA-4.0 and executable
materials AGPL-3.0-only under LICENSE. No constitutional amendment is proposed.
Historical M4 G4 NO-GO and all M4/M3/M3.5 acceptance gates retain their scope.

## Review and acceptance

Review SPEC-039–044, installation effects, portable contracts and negative controls
before adopting the capability. Freeze the exact reviewed candidate. A later
founder decision must identify accepted scope and residual limitations. Passing
structural validation or creating issues does not adopt this ADR.

## Approved scope: native-process billing observation boundary

On 2026-10-11 the owner explicitly approved the process-scoped boundary and
Alternative B operational-subscription semantics. This approves scope only.
An additive registration-v5 contract is being documented; authentic native
evidence remains pending. The overall ADR remains Proposed; neither complete
registration nor provider capture is approved by this decision.

For a registered M4.5 run, a trusted observer binds the launched native Codex or Claude Code process to its subscription route, account namespace, host/build, executable, configuration, exact arguments, model route, candidate and slot. Fresh authoritative included-quota, credits, extra-usage and auto-recharge observations govern bounded launch/session operation. The process must have no API key, helper credential, provider override, paid fallback or alternate-provider fallback. A bounded supervisor polls and stops further work on quota exhaustion, stale/lost observation, identity/configuration drift or its limits. The quota is an operational boundary, not a per-internal-request client-side veto. This scoped statement does not establish account-wide API billing settings or unrelated account activity.

Actual cohort cash remains unknown until independent authoritative verification
covers setup, all started slots and completion reconciliation. Unknown cash is
not zero. Independently verified actual cash remains an acceptance and positive-
utility gate; it is not a precondition before each internal provider request.
The additional-spend cap remains EUR 0, with no purchases, overages, paid API or
paid fallback. The estimated subscription reservation remains a separate
accounting route and is not actual allocation, provider accounting or cash.
Missing, stale, conflicting or unverifiable operational route/quota conditions
refuse launch or stop further work.

This scope approval preserves strict registration-v1/v2 and
subscription-policy-v1 behavior. It creates no observer, cash receipt,
provider-call permission or complete registration. The additive
[operational subscription capture policy](../../specs/044-ai-tooling-evaluation/operational-subscription-capture-policy.md)
uses `agent-braid-m45-operational-subscription-policy-v3` with registration-v5.
Its OP001–OP006 tasks separate source controls from native evidence.
Implementation and evidence require candidate-bound validation and review; this
scope decision does not adopt the overall ADR, which remains Proposed.
