# SPEC-019 authority inventory refresh

The previous SPEC-019 draft used historical authority/evidence commit
`7a8df0d587fbb9e3737c0b8d8af4e298edb0cc86` with human review already pending.
The new preparation increment takes a current snapshot and will freeze its clean
candidate for a new human review. This does not rewrite an approved experiment:
no SPEC-019 experiment/protocol approval or real trained model exists.

Compared with that historical inventory, current `develop` adds ADRs 0020 and
0021 and the runtime operator-grant, policy, preparation-evidence and schedule
schemas. It changes `ARCHITECTURE.md`, assurance levels, Git replay architecture
and scientific integration documents. The Constitution, Governance, accepted
ADR 0017/0018 and anchored-sequence contracts remain byte-identical in the
authority snapshot. The changes predate this increment; no canonical authority
is edited by this preparation PR.

The new inventory is explicit in assurance and does not imply acceptance of any
M4/System One/forecast result. Existing obtained synthetic capture/tooling
artifacts retain their original hashes, commands and limits. Original historical
records remain available in Git. SC-001 through SC-005 still have no obtained
model/evaluation evidence. SC-008 covers preparation software only.

Human review remains pending before and after snapshot/freeze. Technical agent
review, refreshed hashes and a passing profile cannot approve the candidate
scientific protocol or source expansion.

## Upstream moved during validation

Remote `develop` advanced from the preparation base `d5f379be20eb99a584cf71deb853cd68f3722834`
to `e66f9a1b94fc5ebfbf784d9c48a76f53c1a656ee` through PR #462. The inspected
comparison changes M4 records/runtime, architecture status and AI-tooling
assurance records; it changes no SPEC-019 file or normative Constitution/Governance bytes. This increment is
validated against its explicit `d5f379b` base, and its historical freeze will bind
the exact candidate rather than claim validation of later upstream changes.
Integration and any later authority review remain separate decisions.
