# SPEC-019 source feasibility register

**Observed on:** 2026-09-28. **Decision boundary:** the founder approved source
discovery and an eligibility audit, not a dataset, model fit or M3.5 result.
This register covers public repository metadata and already published Agent
Braid artifacts. It contains no private session payloads or utility labels.

## Candidate owned repositories: Kinetiq and SmartNotes

The [prospective pilot runbook](prospective-pilot.md) defines the proposed
implementation route for private disposable labs and an opt-in local sidecar.
As of 2026-09-30 these are tooling preparations: no registration run, real
capture window, actual eligible pair or source-yield estimate exists. The
repo-level screen below remains the only observed count.

**Screened on:** 2026-09-29, at repository/schema/specification level only.
The owners authorized planning these two repositories as candidate workflow
families. This authorization does not grant access to session payloads,
patient records, editor logs, ignored files, or external capture services.
The founder subsequently approved the bounded ADR 0018 architecture and
candidate-source preparation on 2026-10-01; the
[decision record](adr-0018-founder-decision.json) leaves source-specific
permission, privacy, registration and yield gates open.
Neither repository supplied an immutable shared-base event feed or observed
candidate pair in this screen. Therefore each contributes **zero observed
sessions and zero eligible pairs**; these are screening counts, not estimates
of future yield.

| Candidate | Workflow families worth a later, separately authorized screen | Excluded material and current disposition |
| --- | --- | --- |
| Kinetiq | Authored expert rules/decision tables; specifications, ADRs, methodology and contracts; task or roadmap decisions only if a first-party event feed records concurrent edits against one immutable base. | Gait sessions, video, keypoints, biometrics, athlete/client material and processing traces are excluded. Git commits/diffs alone do not establish concurrent insert events. No feed or eligible pair was observed. |
| SmartNotes | Specifications, ADRs, operational docs and task decisions in non-clinical repository authoring workflows, subject to a future opt-in local capture design. | All patient records, `PA-NNNN` material, audio, transcripts, clinical drafts, review/audit events and production traces are excluded. No feed or eligible pair was observed. |

This inventory is based on repository-level architecture, schema, workflow
and policy documents only. It does not inspect patient records, patient event
payloads, private logs, or local application state. Before any capture is
opened, each repository needs its own named source owner, rights/privacy
decision, reviewed capture contract, and a fixed contiguous window. A local
design or synthetic demonstration cannot satisfy those gates.

**Signaling design:** The [instrumentation note](instrumentation.md#recommended-signaling-boundary-for-kinetiq-and-smartnotes)
selects an opt-in Agent Braid sidecar at the proposal boundary. The initial
Kinetiq candidate is an ordered evidence-pipeline decision shortlist; the
initial SmartNotes candidate is an ordered non-clinical architecture/Spec Kit
decision-option list. Each needs a recorded base seen by each real participant
and independent insert proposals before document/PR incorporation. These are
proposed process boundaries, not observed feeds or eligible families. The
current synthetic capture format is insufficient for real sessions and must
not be relabeled as one.

## Discovery frame and reproducibility

The read-only inventory used `gh repo list jayanez --visibility public --limit
100 --json nameWithOwner,url,updatedAt,description`, `gh repo view` for fork
status, the committed M2 corpus manifest, and `git diff --name-status` from
its frozen base to each registered source commit. Repository file discovery
used `rg --files`; a search for `anchorId`, `anchored-sequence-v1`, `utility`
and `annotator` in checked-in JSON/JSONL/CSV/NDJSON found M3 synthetic
fixtures and evidence, but no real session or annotation records. The search
excludes private repositories, ignored files,
unpublished editor logs and uninspected public history. Public visibility is
not a consent record for editing-session data.

| Source considered | Unit inspected | Outcome and reason |
| --- | --- | --- |
| `jayanez/agent-braid` | One directly owned public repository | Potential source owner only. No consent-reviewed `anchored-sequence-v1` session feed or utility annotations identified in checked-in artifacts; no session pair can be counted. |
| `jayanez/azure-sdk-for-net` and `jayanez/azure-functions-extension` | Two public fork metadata records | Upstream projects belong to Azure. No editor-session rights or matching event feed established; payloads were not inspected or admitted. |
| M2 corpus, PRs #137 and #138 at base `f3c734a1f42d6d5962cfedc57d7f6c1efe40e0a6` | Two registered source-commit workstreams (`58351f812614058e53a8ee6aef1dd458f1bb70fc`, `083f1a390988a9527a5aaeb19133401243b1d714`) | **2 source artifacts excluded, 0 admitted session records.** Their recorded units are tracked-file patches, without the immutable sequence base, two insert events, fresh IDs and anchors required for one M3 pair. The two commits must not be relabeled as two sequence inserts. |
| SPEC-018 finite corpus | 130 fixed two/three-operation topology cases | Synthetic laboratory cases; **0 real workload pairs admitted**. |
| `examples/workloads/` | Two declarative AIM fixtures | Illustrative records, not observed editing sessions; **0 real workload pairs admitted**. |

The counts distinguish source artifacts from candidate pairs. Among the two
M2 source-commit artifacts screened for session shape, both are excluded and
none is an eligible pair. This does not estimate the prevalence of eligible
pairs in all Agent Braid history or in any unexamined source. No approved
workload family, prospective session window, adjudicated pair, model training
sample or holdout has been established.

## Owned-flow synthetic instrument

The [local instrumentation demonstration](instrumentation.md) generates a
synthetic event log and applies the M3 request validator without transforming
the proposed operations. Its frozen window covers 18 events in six synthetic
sessions and candidate pairs: one admissible pair and five exclusions, one
each for a wrong base reference, an excessive base, an unsupported operation,
an invalid anchor and missing provenance. Its report states **zero admitted
real pairs**. These counts test sequence, integrity and exclusion accounting;
they do not establish upstream feed completeness, estimate real-source yield
or change the P019-01 gate.

## Admission gate for a future source

Before inspecting session payloads, register the source owner and permission,
editing workflow, participant/data rights, privacy decision, immutable event
feed, and a contiguous collection window with fixed start and end event IDs
or UTC timestamps. The [workload protocol](workload-protocol.md) defines how to
enumerate every session and pair in that window, assign one primary exclusion
reason, freeze family splits and report counts. Do not extend a window to
reach a desired class count; a changed population needs a new reviewed
protocol. If five eligible families or the preregistered label thresholds
cannot be obtained, report feasibility as inconclusive before training.
