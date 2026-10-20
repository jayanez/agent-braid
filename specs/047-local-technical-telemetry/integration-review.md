# Telemetry source integration and retained review

Date: 2026-10-20. Disposition: source integration candidate; pilot **NO-GO**,
operational admission withheld. SPEC-044/T017, SPEC-044/T018 and SPEC-047/T010
remain open. ADR-0025 remains proposed; assurance is draft and human review pending.

## Source and transfer boundary

| Identity | Bound source |
| --- | --- |
| Original rewritten telemetry base | `e474320eb763c33846665a0870677977b47d7a06` |
| Reviewed local telemetry candidate | `b2cf477fe9f9d586d6431ae9ed9a14abb3266706` |
| Public integration base, including PR #557 | `f0854d63a37f3d6dba777dcfd36524d7de37067c` |
| Active identities | Telemetry SPEC-047 / proposed ADR-0025; Plugins SPEC-046 / ADR-0024 |

The net file delta from e474 to b2cf is transferred into an independent clone
of public develop. No private Git commit, branch or tag is imported. The original
telemetry checkout and private admission dossier are not changed by the transfer.
The combined candidate is identified by its PR commit/tree and validation records;
it is not claimed to be the b2cf tree. Existing public plugin and forecasting
changes remain in the resulting source.

The frozen `specs/046-local-technical-telemetry/` namespace, evidence, original
ADR proposals and owner decisions retain their source bytes and candidate scopes.
The active SPEC-047 authority inventory is refreshed against the combined
current authorities; it retains current mode, a null commit, draft stage and
pending human review. The native-plugin SPEC-046 active draft instead retains
both its authority and evidence snapshots at the public integration base
`f0854d63a37f3d6dba777dcfd36524d7de37067c` in historical mode. That public ancestor
preserves the exact pre-telemetry authority and release-evidence input context.
The immutable release record retains its original observed candidate IDs; the
draft snapshot binding does not rebind those observations to the integration
candidate, claim new validation or approval, or adopt ADR-0025.
The initial integration preflight identified the expected stale/incomplete current
authority snapshot after adding the public plugin ADR and telemetry ADR. Its
correction is integration setup, not a collector regression or new acceptance.
The integration controls also identified native-plugin current-input drift after
the telemetry ADR-path additions and CLI changes. Retaining that draft's snapshots
at the public pre-telemetry base preserves the original authority/evidence input
context without editing frozen release evidence or weakening validation. It
supplies no plugin or telemetry acceptance.

## Historical link compatibility correction

The integration repository control found three broken links retained in unchanged
historical documents. On 2026-10-20, navigation-only pointers were added at
`specs/046-local-technical-telemetry/assurance.json`,
`docs/adr/0024-local-technical-telemetry.md` and
`specs/specs/046-local-technical-telemetry/historical/adr-0023-local-technical-telemetry.md`.
They point to the frozen original records and, where applicable, the active
SPEC-047 / proposed ADR-0025 records. They do not introduce active specification
or ADR identities, approval, evidence or authority rebinding. Original frozen
files remain unchanged. The active authority inventory includes the new ADR-path
pointer because it inventories every file under the authority directories.

## Existing independent review — not repeated

The owner authorized one Luna Latest (`gpt-6-luna`) review of exact b2cf in
prior chat `01a143f9-0d1c-7180-a6da-19649622f704`, turn
`01a14e93-5e12-79d1-af18-11a053925053`. Reviewer `/root/review_b2cf`, reviewer
chat `01a14e93-8de8-7c40-82b6-192f2585c4e4`, completed the review read-only.
The reported result was no actionable correctness, privacy, security or
ID-consistency findings. Reported scope: collector, CLI/MCP integration, export,
b137 corrections and 810/b2cf documentary changes. Existing evidence was used;
no tests or validation profiles were repeated. These pointers preserve the
reported result and scope, without claiming additional coverage.

This completed review is reused for unchanged source. The integration-specific
review covers adaptations to current develop and their affected interfaces;
it does not repeat the complete telemetry review. Neither review supplies human,
architectural, founder or operational acceptance.

## Integration-delta review — 2026-10-20

One Luna Latest (`gpt-6-luna`) reviewer, `/root/review_integration`, completed
read-only review of the integration adaptations and their affected interfaces.
No actionable findings were reported. The review covered CLI coexistence and
its added test, the combined inventory, current authority snapshot and evidence/
acceptance wording. It reused the retained b2cf review for unchanged source and
did not repeat tests, profiles or the complete telemetry review. The stable
candidate profile and CI were still pending at review time. This record grants
no operational, architectural, human or founder acceptance.

## Current integration and validation boundary

The CLI reconciliation preserves current plugin and forecasting parsers/dispatch
alongside telemetry. Documentation combines both extension identities and source
inventories. Default-off consent, the numeric aggregate contract, bounded private
storage, manual exchange and b137 failure/retry behavior retain their scope.
There is no new plugin configuration/consent, MCP action, runtime grant or capture.

Historical b137 results remain pre-commit code-delta evidence: 33 telemetry tests
and the PR profile with 1,888 tests / 11 skips. Older C/D results retain their
original boundary. None is relabelled as validation of the combined tree.
Integration-delta review and one stable-candidate PR profile, plus required CI,
are separate current-candidate records. Planned checks are not passing results.
New output must not overwrite the frozen historical evidence folder. The 11
historical skipped controls remain unexecuted within their original evidence.

## Source inventory and remaining gates

The combined source portfolio has eight specifications and 106 task obligations:
78 checked and 28 open, three historically closed parents and five open parents,
114 desired tracking records. The earlier telemetry-only source lot was 65 checked
and 26 open; Plugins contributes 13 checked and two open tasks. Counts describe
source checkboxes and mapped parent states, not current remote issue closure.

[The M4.5 map](../../docs/tooling/M45_ALIGNMENT.md) and [machine-readable alignment](alignment.json)
retain the task and acceptance boundaries. The unpublished tracking drafts are
historical preparation only; a fresh scoped audit, exact new-ID allowlist,
authorized digest apply and readback are required for external tracking writes.

Historical SPEC-044/T004 keeps its approved bounded closure and exclusions. E9
owner decisions stay bound to e9 and do not transfer acceptance to the integrated
candidate. Native/registration/platform evidence, architectural adoption,
human/founder acceptance, operational admission and M4.5 closure remain pending.
Source integration is not product publication, a new package or pilot admission.
