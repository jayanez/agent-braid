# Telemetry identity reconciliation — b13737ed4584

This is the retained local identity-migration account. The [integration record](integration-review.md)
tracks subsequent source transfer and the completed b2cf Luna review. Dated
no-import/no-review observations below retain their original boundary.

This local documentary change is based on commit
`b13737ed4584e512edb054d9a891a0b06fab8120`. It changes current document
identities only. Pilot **NO-GO**, operational admission withheld, tasks open,
T004 unchanged; no architectural or human acceptance is granted.

| Scope | Reserved identity | Current telemetry identity |
| --- | --- | --- |
| Native AI plugins | SPEC-046 / `046-native-ai-plugins` | SPEC-047 / `047-local-technical-telemetry` |
| Native plugin ADR | ADR 0024 / `0024-native-ai-plugins.md` | ADR 0025 / `0025-local-technical-telemetry.md` |

The native plugin identities were confirmed in the existing local checkout at
`/Users/juanyanez/Repos/Personal/agent-braid` (HEAD `3130116`). No remote fetch,
history import, plugin implementation or plugin acceptance was performed. No
public identity was reassigned. The local telemetry tracking drafts have no
published identity claim; their keys now use SPEC-047, including open T010.
SPEC-044/T017 and T018 remain open. Checkbox states are unchanged.

At b137, telemetry was locally named SPEC-046 and its proposed ADR was 0024
(previously 0023). In current references these mean SPEC-047 and proposed ADR
0025. Historical IDs in receipts, owner decisions, authority snapshots, source
manifests, logs and committed evidence retain their original meaning and bytes;
they never refer to the native plugin specification. Owner approvals remain
bound to their original candidates and are not transferred by this mapping.

Active specification, plan, tasks, assurance, contract, validation plan and draft
tracking documents moved to `specs/047-local-technical-telemetry/`. Frozen
records and evidence remain at `specs/046-local-technical-telemetry/`; that folder
is a historical telemetry namespace, not an active plugin specification. For
historical references to moved files, consult `git show b13737ed4584:<old-path>`
or use this mapping for the current document. The original ADR 0024 proposal is
retained at `specs/046-local-technical-telemetry/historical/adr-0024-local-technical-telemetry-b13737ed4584.md`.
The original ADR 0023 snapshot remains unchanged.

The collector code, data format, default-off consent, dependencies, installation
behavior, hosts and providers are unchanged. Test edits only update documentary
IDs and file lookups. Previous validation retains its original pre-commit code
boundary; no tests, profiles, experiments or admission validations were rerun.
This map does not claim independent review or resolve pending admission gates.

Documentary freeze review (2026-10-18): moved-document links and JSON syntax inspected; collector, frozen evidence, authority snapshots, observation contract and SPEC-044/T004 record/block bytes preserved. Telemetry checkbox states are unchanged. No test suite or validation profile was repeated; this inspection establishes documentary consistency only. The native plugin documents are not imported into this branch.
