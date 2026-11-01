# System One: evidence, capability and resumption index

## Current state (2026-11-01)

This section supersedes older statements below. Sections after it are historical
snapshots; their frozen evidence text is unchanged and describes the time it was
written.

- Milestones S1.0–S1.4 (GitHub #13–#17) were closed on 2026-10-31 by founder
  decision as deferred; the remaining open System One issues sit in milestone
  Deferred #24.
- The code is merged in `develop` (via #655). The local Codex checkouts named in
  older sections are historical and are not needed.
- SPEC-051 and ADR 0026 are published in the repository.
- The code has no product callers, no learned model and no observed use; see the
  [completeness audit](addenda/completeness-audit-20261101/README.md).
- Next work is [SPEC-066](../../specs/066-system-one-shadow/spec.md) (track S1.5,
  draft) and [ADR 0034](../adr/0034-system-one-shadow-advisory-boundary.md).

## Latest RF-T01/RF-T02 documentary receipt (2026-10-21)

[Final SPEC-051 local software evidence](addenda/spec051-rf01-rf02-final-20261021/README.md) preserves42 focused controls, corrected quick/PR2153 tests each (2130 passed,23 skipped), the failed first profiles and incomplete OS read, metadata repair, mutation limitations and pending gates. This is corpus publication only: canonical SPEC051/ADR0026/modules/tests remain unpublished in the coordinator's product candidate. Pure validation does not admit real sources, storage, observer, training, human/scientific approval or activation. Earlier proposal/receipt states remain dated history.

Start here, then read the [agent resumption guide](RESUMPTION.md). This is the current reading map as of the documentary review on2026-10-21; individual receipts below retain their own observation times. Chat history and ZIP imports are not required to understand the recorded work.

## Latest T08 delivery and pending-gate record

[Final T08 documentary supplement](addenda/t08-final-20261020/README.md) preserves the two exact local source documents and provides portable links to the complete T02–T07 evidence chain and a G01–G12 synopsis. Both2084-case profiles passed with19 skips each;24 receipts/40 archived members and all2527 prior files were checked. T08 delivers a local documentary candidate, not product/schema adoption, utility, human/scientific acceptance, model promotion or activation. T09 does not start; no task/issue/milestone is closed.

T07 PR609 was integrated into develop as `b52d7ea3542a3c09678c4b69196c9105f8271f4a`. T08 PR610 was originally published against its unmerged branch; the current candidate now contains only T08 changes on that integrated base. The earlier publication/dependency observations remain historical. Documentary integration is separate from product publication and acceptance; the earlier T07 engineering evidence remains bounded, not a universal acceptance result.

## Prior bounded T07 review and conformance evidence

[Final T07 documentary supplement](addenda/t07-final-20261020/README.md) records independent Luna technical review, corrected compatibility controls, five transcribed reviewer executions, preserved failures and both completed profiles. Packet89 bindings/38 archived members/48 raw files were checked; product sources remain unchanged and local. The32-vector mapping supplies predicate-family evidence, not archived recipe replay or scientific accuracy. Human/Claude/scientific/training/admission/promotion/activation and external host adoption remain pending; no administrative or acceptance gate is closed.

T06's documentary corpus was integrated through PR608 at7a9cf27. T07 is a separate supplement; earlier pending-T07 statements below and in frozen T06 receipts describe their earlier observation times. Its publication and any subsequent integration are separate from PR608 and from product publication.

## Prior T06 controlled-consumer delivery

[Final Core/MCP/stdio documentary reconciliation](addenda/t06-transport-final-20261020/README.md) is the latest engineering observation: Core API and controlled real service/stdio-client paths obtained, both transport profiles passed, final packet verified. It links failures, repairs, exact sources, logs and cost limits across all epochs. Independent product review/T07, host adoption and scientific/human/admission/promotion/activation gates remain pending. Product source is retained locally, not published by this documentary branch.

The following local observations and PR594 handoff preserve chronology. Their pending statements apply to their recorded dates; use the final reconciliation above for the latest engineering status. This branch's new documentary PR and integration receipts remain separate from already merged PR594.

## Subsequent local T06 evidence

[Core API documentary intake](addenda/t06-core-intake-20261020/README.md) preserves pre-fix/fixed/final-test capture epochs, scoped review/fixes, source hashes and descriptive costs. The [final Core-only reconciliation](addenda/t06-core-final-20261020/README.md) now records completed quick/PR and a verified final local package; the earlier intake remains an observation from before completion. This local branch increment is separate from integrated PR594 and contains no product implementation.

## Subsequent local MCP/stdio intake

[Transport intake](addenda/t06-transport-intake-20261020/README.md) preserves design, fixture failures, mutation test gap/repair, three capture epochs and source hashes. Final focused capture is obtained. The later [profile receipts](addenda/t06-transport-profiles-20261020/README.md) record both full profiles passed on2415 identical inputs; final packaging remains pending. These supplements remain local.

## Historical PR594 handoff

T05 internal engineering is delivered: [final packet and verification](addenda/t05-final-package-20261020/README.md), [full-profile receipts](addenda/t05-profiles-final-20261020/README.md) and [scoped Luna row-cap disposition](addenda/t05-rowcap-luna-disposition-20261020/README.md). Both full profiles recorded2042cases,2023passed,19skips,zero failures each; tests overlap and are not independent scientific observations. Packaging failures are preserved with their repairs;72packet bindings,22source-archive members and20reversible raw logs were checked.

The following PR594 status is a historical integration snapshot; subsequent local Core evidence is linked above. The later T06 Core API assignment belongs to the coordinator's separate implementation conversation. This PR contains no T06 implementation or completed T06 evidence. See the [chronology/status clarification](addenda/pr594-documentary-review-20261020/status-clarifications.md) for that later authorization, the earlier conditional T05 GO and frozen DDP-T01 headers. DDP-T01 revision2 was verified by the coordinator for bounded planning; its frozen pre-disposition headers do not override that later receipt or imply public adoption.

The corpus is published in [PR594](https://github.com/jayanez/agent-braid/pull/594), targeting develop; publication, current-head CI, review and integration are separate. Product source/tests/fixtures/config/source archives/patches remain in the explicitly hash-bound coordinator package. The [publication receipt](addenda/github-publication-20261020.md) records initial publication, not current CI. No scientific/human approval or activation follows from publication or software tests.

[PR594 documentary review and integration preparation](addenda/pr594-documentary-review-20261020/README.md) records chronology corrections, the bounded Luna recheck and mechanical checks; current-head CI and merge remain separate.

## Core reading and traceability

- [Evidence and evolution](evolution.md): why each increment happened, positive/negative findings and domain limits.
- [Evidence register](evidence-register.json) and [faithful report/protocol snapshots](source-documents.json): stable study/task aliases, hashes, line references, commands, resources and unknowns. Original paths/links describe research-source provenance.
- [Capability map](../../specs/028-system-one-core/decision-delivery/program-map.md), [bounded architecture](../../specs/028-system-one-core/decision-delivery/architecture.md) and [latency/budget boundaries](../../specs/028-system-one-core/decision-delivery/latency-and-budgets.md).
- [Canonical task aliases](task-map.json), [historical gates](gates-and-assignment.md) and [historical requirements checklist](review-checklist.md). Read their pending observations with the later receipts below, not as current status.
- [Adversarial review brief](adversarial-review.md): review questions for Claude Code or another reviewer. No Claude Code review is claimed; scoped AI code reviews in later receipts are separate from global T07 and human/scientific acceptance.

## Historical receipt map

Rows identify frozen observations and later dispositions; a pending or active status inside an older receipt is not a current assertion.

| Stage | Evidence and later disposition |
|---|---|
| T025 development and final engineering | [Development snapshot](addenda/t025-development-20261020.md), then [final engineering/assignment](addenda/t025-final-20261020.md) |
| Corpus/Project/DDP-T01 reconciliation | [Continuity receipt](addenda/verification-continuity-20261020/README.md):88-item Project readback, original failed full profile and localized correction, final coordinator design disposition |
| Initial component assignment | [Preparation handoff](addenda/ddp-t02-t04-preparation-20261020.md) |
| T04 component and serial pin | [Pre-pin component](addenda/t04-component-20261020/README.md), then [T02 and actual pin](addenda/t02-and-serial-pin-20261020/README.md) |
| T03 and component join | [T03/52-case join](addenda/t03-and-component-join-20261020/README.md), [profile start](addenda/component-profiles-started-20261020.md), then [final2014-case profiles](addenda/component-profiles-final-20261020/README.md) |
| First component final package/T05 GO | [Final first batch and T05 assignment](addenda/first-batch-final-package-20261020/README.md); earlier [conditional authority](addenda/publication-and-t05-condition-20261020.md) |
| T05 context and review plan | [Lifetime/digest directions](addenda/t05-context-and-digest-seams-20261020.md), with later source-bound implementation and review below |
| T05 failure/candidate chronology | [Caught-failure finding and failed22-case attempt](addenda/t05-failure-latch-20261020/README.md), [admission/refusal directions](addenda/t05-failure-latch-20261020/admission-and-late-refusal.md), [review candidate](addenda/t05-review-candidate-20261020/README.md) |
| T05 row-cap review and correction | [Original Luna P2/reproduction](addenda/t05-luna-row64-review-20261020/README.md), [fixed candidate](addenda/t05-rowcap-fixed-candidate-20261020/README.md), then [targeted disposition](addenda/t05-rowcap-luna-disposition-20261020/README.md) |
| T05 joined/full validation | [80-case join and profile start](addenda/t05-join-and-profiles-start-20261020/README.md), then [final2042-case profiles](addenda/t05-profiles-final-20261020/README.md) |
| T05 packaging integrity | [One-log attributes exception](addenda/t05-whitespace-preservation-20261020.md), [link-check failure](addenda/t05-packaging-link-failure-20261020/README.md), then [final packet/retained failures and repairs](addenda/t05-final-package-20261020/README.md) and [post-seal artifact check](addenda/t05-final-package-20261020/post-seal-check.md) |

## Source and acceptance boundary

Research-source snapshot: /Users/juanyanez/Repos/Personal/agent-braid-system-one, observed HEAD48f4226db1e1b0565b1f8faf0eca81c150a65d30 plus substantial WIP. Report/protocol hashes identify actual working bytes; HEAD alone does not reproduce them. Models, raw datasets, custodian labels, private histories, generators, runtime source and large artifacts are not bundled by this documentary delivery. Missing local inputs must be reported, never reconstructed as obtained evidence.

The capability package and verified-plan public schemas remain proposals; the later component/T05 records establish bounded internal engineering only. Six spec parents and five S1 milestones remain open at the recorded tracking snapshot. Broader T07 review, human/linguistic and representative workflow acceptance, independent scientific reproduction, source rights, training/calibration, admission/promotion and activation remain separate pending gates.

No general calibrated reliability, theorem, Laya parity or unrestricted language understanding is claimed. Deterministic admissibility is not calibrated probability; controlled EN/ES roundtrips and software/AI review do not supply human or scientific approval. Acquisition, layer1decision and complete native preparation have separate costs; no deadline/speedup is inferred from provisional timing.

## Documentary continuity

Before delivery, incorporate every material result, failed attempt, correction, review, decision and handoff with task/requirement mapping, exact sources/hashes, observation boundary, obtained result, validation scope and unresolved gates. Link details instead of duplicating them. Preserve frozen records and clarify supersession additively. Keep current navigation distinct from history, and local incorporation/publication/integration distinct from product implementation or acceptance. ZIPs are derivative snapshots; chat acknowledgements alone do not complete corpus incorporation.

## Bounded v1 final engineering and continuation (2026-10-21)

Read the [final publication-closure supplement](addenda/v1-publication-closure-20261021/README.md) for the later local preparation, final SDK/Codex engineering, failures, exact source capsules and pending gates. Earlier pending entries retain their dated observation boundary. The [RF feedback proposal](addenda/v1-publication-closure-20261021/forecast-feedback-proposal/README.md) is planned work, not accepted collection or implemented telemetry. Combined-candidate review/CI/publication remain the final coordinator's separate receipt; this index edit supplies no scientific/human/promotion/activation acceptance.
