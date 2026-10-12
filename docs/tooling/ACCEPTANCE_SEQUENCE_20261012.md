# M4.5 acceptance sequence and decision packet

Status: owner accepted the bounded SPEC-039/040/042 scopes and authorized FC.1
contract review/preparation on 2026-10-12. PR #502 integrated those decisions,
and the six bounded issues are closed. Preparation baseline: public `develop`
`d58b648a36b1f8477204004e3acbaad5e40f83b7`, inspected on 2026-10-12.
The owner requested closing every currently supportable item so FC.1 can be
addressed, while retaining the deferred two-person human evaluation.

## Delivery rules

Use the existing SPEC-039–044 task lists and GitHub issues; do not create a
duplicate backlog. Keep the historical M4 plan in `tasks/plan.md` unchanged.
Allow at most 20 minutes of owner interaction per session, in at most two
grouped decision blocks. Technical lots are limited to 90 minutes; publish a
checkpoint with completed work, exact blockers and the next action at the limit.
Stop an admission investigation after 30 minutes if a required authoritative
source is unavailable. One inspection plus one directed correction per blocker
is sufficient; do not repeat whole-program audits.

Existing rights, model/effort, human-deferral and accounting decisions retain
their actual scope. No paid API, credits, overage, auto-recharge or fallback;
additional spend remains EUR 0. Preserve the EUR 5.045 estimate convention as
an estimate, never as actual cash or subscription allocation. Measurements
are serialized; FC.1 and M4.5 never share a measurement window.

## Lot 1: three bounded acceptance decisions

The owner's direct interactive answer was
`Aceptar las tres con esos límites (Recomendada)` to question item
`["request_user_input_async","call_f2af6fd4f85244cfa0b4b4c3f2ec7cd3",0]`.
The actual decisions are recorded separately for
[SPEC-039](../../specs/039-ai-tooling-program/founder-review-20261012.json),
[SPEC-040](../../specs/040-portable-mcp-surface/founder-review-20261012.json) and
[SPEC-042](../../specs/042-ai-tooling-packaging/founder-review-20261012.json).
Source T010 checkboxes, assurance review states and parent dispositions now
propose the six closures listed below. No remote issue was closed by recording
these decisions; merge authorization and governed apply remain separate.

The [verification receipt](evidence/acceptance-preparation-20261012.json)
checks all 24 canonical scenario projections, 552 historical input hashes,
obtained-evidence hashes, nine completed task IDs per spec, and 12 historical
review input hashes. All historical hash checks passed. This main-session
inspection is not a new independent review or a reinspection of private raw
archives. The complete later paired procedures, rather than the incomplete
e40 archives in the [retention update](EVIDENCE_RETENTION_20261010.md), support
these proposals.

| Decision | Exact proposed acceptance | Obtained evidence | Proposed tracking after acceptance |
| --- | --- | --- | --- |
| A / SPEC-039 | Documentary program, scope, subordinate traceability, architecture proposal, provenance and governed tracking obligations; preservation of native/human/founder closure gates. No adoption of ADR 0021. | [SC-001–008](../../specs/039-ai-tooling-program/evidence/sc-001.json), source `5cffa9d27f27686dc2cbbf90ed643e2ec2df94e7`; [T009 validation](../../specs/039-ai-tooling-program/evidence/technical-validation.json). All eight individual receipt hashes are indexed in the verification receipt. | Record the actual decision, complete T010/#405 and close parent #395 if accepted. |
| B / SPEC-040 | Optional pinned MCP SDK stdio adapter, local service/protocol parity, typed outputs, trusted roots, grants/refusals, cancellation/recovery and resources/prompts within the paired local controls. | [SC-001–008](../../specs/040-portable-mcp-surface/evidence/sc-001.json), source `24921e1a16dfff15cde5af091f7b955491acdbef`; 37 passing tests and eight cases recorded in the source receipt; [T009 validation](../../specs/040-portable-mcp-surface/evidence/technical-validation.json). | Record the actual decision, complete T010/#416 and close parent #406 if accepted. |
| C / SPEC-042 | Receipt-owned package assets and installation lifecycle, preservation, diagnostics, update/removal and package provenance within recorded standalone platform controls. | [SC-001](../../specs/042-ai-tooling-packaging/evidence/sc-001.json) and [SC-008](../../specs/042-ai-tooling-packaging/evidence/sc-008.json), plus the six indexed lifecycle receipts. Local source `5cffa9d27f27686dc2cbbf90ed643e2ec2df94e7`; package source `53f1704ca7ea668637efdeb2d4b0a231769b3c68`; installed macOS ARM64 and explicitly emulated Linux AMD64. [T009 validation](../../specs/042-ai-tooling-packaging/evidence/technical-validation.json). | Record the actual decision, complete T010/#438 and close parent #428 if accepted. |

The [independent technical review](../../specs/044-ai-tooling-evaluation/evidence/technical-review.json)
records designated Luna Latest at medium effort on
`72a396d294205201f7f56d00fa2349dccb540a5c`; its record explicitly has no tool-runtime
attestation. The quick and PR profiles each recorded 1,293 tests, including 12
skips. Those are historical results, not fresh tests on the baseline above.
Resolved findings and accepted scope remain in the linked record.

Review inputs have subsequently changed. For these three specs, the task-list
delta from the reviewed source only checks T009 and links its validation
receipt. SPEC-040's captured product inputs have no current drift. SPEC-042's
input drift is the historical-to-current validation-plan wording and optional
SDK test guards; the later SPEC-040 capture includes those guards. SPEC-039's
documentary inputs include later task/evidence annotations and additive approved
process-policy text in ADR 0021. The complete path lists are retained in the
verification receipt. Do not transfer old observations to changed bytes or
interpret bounded acceptance as acceptance of every later addition.

Every card excludes native Codex/Claude observation, the registered SPEC-044
clean reproduction and 108-attempt evaluation, positive utility, human ratings,
whole-ADR adoption and whole-M4.5 closure. At the inspected baseline, authority
snapshots retained `f18f63c8fc9b52dc0652f57c505d7f7647164030` and evidence snapshots
were current. The official freeze command was subsequently run on a clean
candidate for each spec, with both authority and evidence snapshots bound as
follows. No runtime code, evidence projection or original observation was changed.

| Spec | Frozen authority/evidence packet commit | Human decision |
| --- | --- | --- |
| SPEC-039 | `e94497bd561d03bac858ba154e21d9327437d22e` | Accepted within card A |
| SPEC-040 | `588873779b74865563fafc3fa507884b2e88751b` | Accepted within card B |
| SPEC-042 | `6eedc5f14d9d8188a14b25d0820693d269ef9253` | Accepted within card C |

The authority inventory now includes the previously approved additive policy
text disclosed above. Freezing recorded its bytes and reset human review to
pending. The later direct owner response, not the freeze, approved the bounded
cards. It did not adopt the whole ADR or accept every later addition. Each
original observation keeps its actual earlier source candidate. The review
records bind the actual response to each corresponding frozen packet.

## Lot 2: admission disposition

The bounded inspection found the production interfaces for caller-supplied
preparation, process-route and operational-route verifiers in
`agent_braid/tooling_hosts.py` and `agent_braid/tooling_supervisor.py`, but no
shipped concrete native operational-source verifier in `agent_braid/` or
`scripts/`. Test implementations are synthetic. An external private verifier
could exist; its identity, source and trusted receipts are not established by
this inspection. The historical private registration draft is not authenticated
or approved by this packet.

Read-only executable version checks on 2026-10-12 reported Codex CLI
`0.162.0-alpha.17.2` and global Claude Code `2.1.285`. The latter is below the
adapter's documented `2.1.286` minimum. The previously prepared isolated
`2.1.287` binary remains historical preparation until its present identity and
effective namespace are verified. No global installation or preferences were
changed; no authenticated account contents were printed or provider launched.

| Gate | Required next evidence | Disposition |
| --- | --- | --- |
| OP001–004 / native admission | Supported executable, exact effective configuration/argv/account namespace, authoritative fresh quota and disabled paid controls, source-bound live observer/verifier and isolation receipts. Required token/resource observations and cap enforcement must cover their full registered boundaries; local sampled metrics alone cannot clear them. | Blocked on authentic external bindings; user approval cannot substitute for observed facts. |
| SPEC-044/T001 / exact registration | Bind those sources to the exact candidate/wheel, 18 fixtures, six prompts, all 108 slots, frozen rubric, abstract roles and numerical caps; verify existing rights/deferral decisions. | Specific registration/capture approval follows a complete packet; not requested while inadmissible. |
| SPEC-044/T004 / reproduction | Registered native macOS ARM64 and owner-selected standard GitHub Actions Linux x86_64 receipts. | Depends on approved registration; standalone emulated Linux checks cannot substitute. |
| SPEC-044/T006 / acceptance costs | Independent cohort-attributable cash verification and actual technical measurements; unknown reviewer time/fees remain unknown. | Estimate approval is already recorded; acceptance cash evidence remains unavailable. |

Admission is parked at these concrete blockers. Do not fabricate a verifier or
translate unlaunched roster entries into 108 attempted refusals. Do not ask for
fresh billing-period details, copy credentials, authenticate a new namespace,
upgrade global CLIs or launch provider work as a workaround. Reopen this lot
when a named, source-backed binding or a concrete supported-host correction is
available; any necessary interactive step must be presented as one grouped
checklist with its effects.

## Lot 3: remaining native and registered work

Only after complete registration approval and admission:

1. Obtain both hosts' five-skill and journey receipts, covering SPEC-041/T001–008,
   SPEC-043/T001,T003,T008 and SPEC-044/T002; reuse one authentic observation for
   multiple requirements only when its exact assertions cover each one.
2. Obtain registered reproduction T004, then process the complete frozen T005
   roster with its prescribed order and isolated sessions. Retain every actual
   interruption, refusal, stop and unavailable value without outcome-driven
   revisions or silent retries.
3. Reconcile T006 technical costs and T007 technical interpretation; run T009
   validation, then prepare T008 and its independent technical review. Present
   SPEC-041/T010 and SPEC-043/T010 together when their original observations and
   T009 predecessors are complete.

T007's human portion and SPEC-044/T010 stay pending for the separately bound
two-person evaluation and adjudication. Technical completion cannot mark a
partially complete original obligation done. No new auxiliary issues are
created merely to improve closure counts.

## Lot 4: FC.1 entry and integration

The [FC.1 entry packet](FC1_ENTRY_20261012.md) identifies reusable contracts and
the first SPEC-034/T001 review package. The owner explicitly lifted the earlier
pause only for contract review and first-lot preparation. This work can proceed
while native admission and human evaluation are parked. Implementation still
requires its own exact-scope decision. Real workload collection, model
download/loading, experiment launch and promotion retain separate gates.

After actual acceptance, update the existing task, assurance, review and parent
tracking records; prepare the reviewed integration candidate. Ask for merge
authorization separately from acceptance, in the same grouped block if useful.
After authorized merge, apply only the reviewed milestone-19 audit digest and
require a second scoped audit with `operations: []`. Verify private Project
membership/status separately or report its access limitation. Do not apply an
unrelated global tracking delta. At preparation time all six parents and milestone
19 remain open. Parent closures are individual; milestone 19 stays open while
registered/native or human acceptance requirements remain pending.


## Integrated closure and retained history

[PR #502](https://github.com/jayanez/agent-braid/pull/502) was squash-merged as
`a7f7d5890942ef2eb657f4a783b974afa589b339` after the owner separately authorized
integration and the six closures with `OK continúa`. The corrected isolated local
PR profile passed 1,344 tests (12 declared skips) and every selected executable
gate; exact-candidate CI passed 1,344 core tests (eight declared skips) and 37
isolated MCP tests. The specialist matrix was skipped by classification. The
earlier local system-Python PATH failure remains disclosed on the PR. No local
validation exception was used.

The reviewed milestone-19 digest
`f1a9d445de0cf84873b6a9b0abbd054e3010377abdb66bffe4a3bbdd7391196b` applied
only #395/#405, #406/#416 and #428/#438. Their pending labels were removed and
actual decision/closure notes recorded; all six Project items were observed as
Done. The subsequent scoped audit returned `operations: []`. Milestone 19
remains open with 58 closed and 27 open issues at that readback.

Squash integration made the newly frozen commits non-ancestors of `develop`.
The public reviewed-history catalog therefore retains each exact annotated tag
and the SHA-256 of the already-published assurance and owner decision. This uses
the existing strict historical validation route, preserving root manifest bytes,
accepted record bytes and original observation commits. A retained tag does not
create a new approval or extend its scope. The three retained references are
`spec-039-reviewed-e94497b`, `spec-040-reviewed-5888737` and
`spec-042-reviewed-6eedc5f`.
