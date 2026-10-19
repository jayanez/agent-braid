# Consolidated plugin, telemetry and FC identity record

Date: 2026-10-17. Disposition: **NO-GO** for the proposed plugin + telemetry
economic scenario; [admission reasons and stop rule](economic-admission.md).
This is a documentary reconciliation, not a new specification or ADR adoption.

**Current integration pointer — 2026-10-20:** the [telemetry integration record](../047-local-technical-telemetry/integration-review.md)
tracks the source transfer after this allocation was merged in PR #557. The
table, inventory hashes and local/uncommitted observations below describe the
2026-10-17 allocation batch; they are not the current integration status.

| Owner | Current identity | Historical local identity | Integration state |
| --- | --- | --- | --- |
| Native AI plugins | SPEC-046 / `046-native-ai-plugins`; ADR-0024 / `0024-native-ai-plugins.md` | Unchanged | Published source on `develop` at `48f4226db1e1b0565b1f8faf0eca81c150a65d30` |
| Local technical telemetry | SPEC-047 / `047-local-technical-telemetry`; proposed ADR-0025 / `0025-local-technical-telemetry.md` | SPEC-046 / `046-local-technical-telemetry`; proposed ADR-0024 (previously local ADR-0023) | Owner-applied documentary migration, local and uncommitted over `b13737ed4584e512edb054d9a891a0b06fab8120`; not in this PR |
| FC.1 and FC.2 | Existing SPEC-034–037/045 identities | Unchanged | Coordinated NO-GO; accounting work and its separate admission gates remain separate |

SPEC-047 and ADR-0025 are allocated to telemetry for subsequent integration.
Do not create another active feature using these IDs. No public ID is reassigned.
A historical telemetry reference to SPEC-046/ADR-0024 must be interpreted with
its source candidate; it must never resolve to the native plugin authority.
Task numbers retain their specification namespace. In particular SPEC-044/T004
is unrelated to either extension's T004 and retains its existing bounded scope.

## Source migration and historical preservation

The telemetry owner moved twelve active documents from
`specs/046-local-technical-telemetry/` to
`specs/047-local-technical-telemetry/`, moved its proposed ADR to
`docs/adr/0025-local-technical-telemetry.md`, and updated active documentation,
local tracking drafts and documentary test lookups. Original frozen records
remain at their original paths. Original ADR proposals remain historical
snapshots. Decisions, receipts, contracts and authority snapshots retain their
original bytes, hashes, candidates and pending acceptance boundaries.

The [inventory](identity-reconciliation.json) binds each active old/new document
and the retained historical files to SHA-256 values observed during this batch.
It records a local source observation, not a new experiment, proof of normative
alignment, fresh validation of telemetry or endorsement of its unchanged code.
Its owner map is `specs/047-local-technical-telemetry/identity-reconciliation-b13737ed4584.md`
in the telemetry candidate. These paths describe that candidate; they are not
links to nonexistent files in the public plugin tree.

## One documentary lot and integration boundary

This PR consolidates the shared identity allocation, migration inventory and
NO-GO on the existing public plugin base. Telemetry has no verified remote
branch or PR base. Publishing its unmerged source merely to create a stacked PR
would include implementation outside this documentary scope. Accordingly its
actual renamed source files remain in the owner's checkout, unchanged by this
batch. Full source migration integration is **pending**, not represented as done
by this map. This PR does not publish the telemetry branch or copy its private
records. Its later integration must use the allocated names, validate current
references and assurance against the resulting candidate, and preserve frozen
snapshots; no existing owner approval automatically transfers.

FC.1 and FC.2 confirmed that their source-bound ledger adds no plugin economic
actions or forecast/grant binding. Their local `real-utility-resumption.md`
coordination section retains the same gate; this common record supplies the
resolved allocation without changing that implementation branch. There is no
viable admitted pair of equivalent actions for the proposed analysis-only
scenario. Do not add a scheduler, binding stub, MCP action, capture or model
runner to manufacture one. Product telemetry aggregates remain outside causal
experimental admission; the fixed-runtime pilot and its budget remain separate.

No task, issue, milestone, human review or scientific acceptance closes here.
No hosts, models, workload captures, installations or provider operations are
part of this batch. Merge is not authorized.
