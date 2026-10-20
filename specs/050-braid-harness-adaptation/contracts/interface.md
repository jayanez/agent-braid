# Braid Harness capability profile contract proposal

Status: draft design, not an implemented or adopted API. Extend the HAR.1/HAR.2 records rather than redefine their authority semantics.

- ComponentProfile: version, component inventory, parent/derived source, host support matrix, immutable path/content/effect policies, lazy context limits, tool/event/role schemas and license provenance.
- SearchPlan: source/base/profile identity, sequential depth/parallel width, full trial DAG/lineage, equal-budget comparator, reservation and stop rules. Proposal, transport and selection retries are separate counted attempts.
- OrchestrationProfile: ownership, declared dependencies/effects, role-specific bounded context, handoff/output contracts and serial-reference verifier. Unknown interactions cannot be asserted independent by model text.
- AutomaticPolicy: exact adopted eligibility/version, independent evidence/regression/cost gates, disabled/shadow/canary/active/stopped state, operator authority and rollback target. Generated policy text is never its own adoption record.
- LifecycleEvent: source/profile/host identity, actual transition/actor/evidence, migration/rollback links, private retention/export disposition and incident or drift reason.

Install task-local components only within a reviewed qualified effect contract. No profile may modify canonical authorities, acceptance verifiers, permission issuers, global settings or unrelated workspaces. Plugin/tool-loop components have distinct provider support; syntax acceptance is not execution qualification.

Activation needs exact applicable evidence and authority. Version migration, interruption, rollback and uninstall retain auditable state and previous usable profiles. An explicit native refusal is required when containment, authentication route, zero-spend conditions, outcome checks or observation support are unavailable. Advice returns executionAuthorization=false; future execution interfaces require separate contract adoption.
