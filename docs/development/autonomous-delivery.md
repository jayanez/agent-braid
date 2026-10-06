<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Autonomous engineering delivery

**Recorded:** 2026-10-06. This non-normative record covers the approved
engineering work that could proceed without new scientific, source-owner or
founder decisions. The [Constitution](../../CONSTITUTION.md), applicable ADRs and
frozen evidence retain their authority. A reviewed PR is the delivery boundary;
merge and whole-milestone acceptance remain separate.

## Parallel tracks and integration

Three implementation tracks used independent full clones from public
`develop` commit `f1bc304827b26c2cc3e02d5488ff2f82daa5453d`, with restored public
Spec Kit history and passing preflights. The existing shared object store was
preserved. Implementation increments were composed on one delivery branch;
tracking and README work followed the obtained results.

| Track | Owned work | Obtained result |
| --- | --- | --- |
| A — M3.5 readiness | Synthetic capture, recovery, pair accounting, filtered-lab and seal checks; read-only private metadata audit | 44 focused tests passed; exact fixture reproduction and all-pairs rehearsal obtained. [Readiness and remaining gates](m35-technical-readiness.md). |
| B — M4 cost | Invocation-local preparation reuse, run-local executor reuse, direct singleton waves and diagnostic profiling | Budgets and independent consumer reconstruction retained; regression and forged-record controls added. [Cost diagnostics](M4_RUNTIME_COST_DIAGNOSTICS.md). |
| C — Linux execution | Public hosted x64 workflows, synthetic reproduction, optional same-host cost comparison and log transport | M3.5 and M4 Linux jobs executed successfully at exact candidate `734feca`; [runbook](linux-experiments.md) and permanent public records obtained. |
| D — Governed tracking | Apply the reviewed merged-source audit; verify private Project views and custom statuses | 42 operations applied; subsequent repository audit reported no operations. All three Project views and four Review pending entries verified at the captured baseline. T014 source completion subsequently merged; see the post-merge status below. |
| E — Documentation | Working capability map, tested runtime-only tutorial, architecture diagram, evidence boundaries and README | [Owned tutorial](../../examples/runtime/README.md) reproduced with no development dependencies; README finalized after experiment results. |

The work changed no runtime dependencies, model-host credentials, private
workflows, billing plan or runner registration. New tests target preparation
budgets, executor behavior, public experiment transport and invalid measurement
records; they do not replace the frozen measurement protocol.

## Executed Linux reproduction

[Public run 37416200890](https://github.com/jayanez/agent-braid/actions/runs/37416200890),
attempt **1**, completed successfully on 2026-10-06. Both caller workflow and
reproduced candidate were
`734feca3e32b8e729a894a6089838a6de2e8ddb8`; the workflow ref was
`work/autonomous-delivery-20261005`. Both jobs used Ubuntu 24.04 hosted
**Linux x86_64**, **Python 3.12.14** and **Git 2.55.0**, with real runner names and
executed steps.

| Reproduction | Result | Observation |
| --- | --- | --- |
| M3.5 synthetic journal/lab/seal controls | **44 tests passed**, no skips or expected failures | 18 fixture events, six examined pairs, one admitted **synthetic** pair and **zero admitted real pairs**; execution authorization remains false. |
| M4 core/policy/scheduler/stdio peer | **68 tests passed**, no skips | Owned fixed-patch fixtures, deterministic protocol peer and controlled process interruption; no model or real-host exercise. |

Neither run changed its bound inputs or working tree. Public records were
extracted byte for byte from complete log blocks after validating their
advertised SHA-256 values; raw test logs match the digests in the reproduction
records. The cost comparison was independently regenerated from the archived
profiles and matched the published comparison byte for byte.

Permanent public files are in
[the evidence archive](../experiments/evidence/autonomous-delivery-2026-10-06/):

- [Hosted Linux receipt and all file digests](../experiments/evidence/autonomous-delivery-2026-10-06/hosted-linux-receipt.json).
- [M3.5 record](../experiments/evidence/autonomous-delivery-2026-10-06/m35-synthetic-reproduction.json)
  and [raw test log](../experiments/evidence/autonomous-delivery-2026-10-06/m35-synthetic-reproduction.txt).
- [M4 record](../experiments/evidence/autonomous-delivery-2026-10-06/m4-alpha-reproduction.json)
  and [raw test log](../experiments/evidence/autonomous-delivery-2026-10-06/m4-alpha-reproduction.txt).
- [Baseline profile](../experiments/evidence/autonomous-delivery-2026-10-06/m4-baseline-cost-profile.json),
  [candidate profile](../experiments/evidence/autonomous-delivery-2026-10-06/m4-candidate-cost-profile.json)
  and [descriptive comparison](../experiments/evidence/autonomous-delivery-2026-10-06/m4-cost-comparison.json).

These records bind `734feca`; later documentation and tracking-source changes
require their own PR validation. Logs and job summaries supplied transport;
the committed public archive supplies durable copies. No private payload or
private evidence reference is included.

## Descriptive full-cost comparison

The unchanged owned two-edit treatments ran in fresh interpreters on the same
Linux VM: six candidate pairs, followed by six baseline pairs. Each capture
retained the frozen serial-first/parallel-first alternation. OS cache and
background activity were uncontrolled. The candidate profiler instrumented
both clean checkouts; fixture, frozen protocol, measurement script, environment
and instrument hashes matched.

| Median full treatment cost | Baseline `f1bc304` | Candidate `734feca` | Observed change |
| --- | --- | --- | --- |
| Serial wall time | 5.360 s | 5.324 s | 0.67% lower |
| Parallel wall time | 9.118 s | 7.647 s | 16.13% lower |
| Serial Git commands | 485 | 485 | Unchanged |
| Parallel Git commands | 821 | 695 | **126 fewer** |
| Serial / parallel bounded budgets | 13 / 20 | 13 / 20 | Unchanged |

All compared result trees were verified and equivalent. The command reduction
removes three redundant preparation reconstructions of 42 Git commands each;
it does not remove consumer verification or enlarge any budget. Producer scratch
is retained only inside one fresh invocation and disposed before its return.

Parallel execution still cost more than serial on this fixture: the candidate's
median paired serial/parallel wall ratio was **0.6963**, with a
`negative-or-null-descriptive` utility outcome. Inclusive nested phases must not
be summed; process-lifetime RSS and sampled scratch peaks have their recorded
limits. Instrumentation and cleanup are included in total wall time. These small
observations establish neither causality nor general speedup and do not amend
the historical ratio **0.5581**, frozen records or the
[G4 NO-GO](../../specs/021-m4-alpha-runtime/g4-decision.json).

## Validation and review boundaries

The composed engineering candidate `734feca` passed the planner-selected
sensitive profile: **417 tests**, with **four explicit skips**, plus repository,
contract, release/publication, scientific, Spec Kit, rendering, replica and
whitespace checks. The skips cover three deferred SPEC-019 model/evaluation
scenarios and one intentionally unavailable private historical commit. They
are not passed scenarios.

An earlier isolated track-B quick profile failed one MCP disconnect/resume test
among 397 tests. Resume rejected portable evidence during fresh reconstruction,
before consuming the resume grant. Its generic error did not retain enough
detail to establish a cause. The same narrow test then passed on the baseline
(39.237 s) and corrected candidate (35.986 s); the composed sensitive suite and
hosted M4 reproduction subsequently passed. Concurrent-load attribution remains
unproven. No budget, refusal or verification rule was relaxed to obtain a pass.

Independent **gpt-6-luna (Luna Latest)** review found an invalid-metric comparator
defect; it was corrected with negative, boolean, zero-divisor, phase and budget
consistency controls. Subsequent review of the composed code, workflows and
tutorial at `734feca` found no actionable findings. The final documentation and
tracking proposal receive their own review, and the final PR candidate must pass
the [PR profile](VALIDATION_PROFILES.md) and complete hosted PR checks.

The owned tutorial was executed literally in a pristine runtime-only virtual
environment. It generated its own Git fixture, completed private execution and
independent result verification, and left source bytes and refs unchanged. It
uses neither `tests` helpers nor `jsonschema`. Structural checks, fresh-process
reproduction, internal review, external validation and founder decisions retain
their separate meanings.

## Tracking and source gates

The [tracking receipt](../experiments/evidence/autonomous-delivery-2026-10-06/tracking-receipt.json)
binds the applied merged source to `f1bc304`. Reviewed plan SHA-256
`ce4dd4ea4270e0b00be7d8349438554ac2c814dd83e5c1d92fa5ef0682477c18`
created 15 SPEC-021 issues, linked 14 subissues and closed 13 completed task
issues. The post-apply repository audit reported `operations: []`.

At the captured baseline, the existing signed-in browser session verified **Specs and tasks**, **By
milestone** and **By status** in the private Project. Its 180 items comprised
165 Done, 11 Todo, zero In Progress and four Review pending. SPEC-021's
[parent #204](https://github.com/jayanez/agent-braid/issues/204) and
[T014 #218](https://github.com/jayanez/agent-braid/issues/218) remained Todo in
M4; T001–T013 were Done. The four mapped pending reviews were SPEC-002,
SPEC-002/T006, SPEC-011 and SPEC-011/T008. CLI access to the private Project
lacked `read:project`; browser verification obtained the required observation
without changing credentials, scopes or Project fields. Temporary filters were
restored.

The T014 checkbox amendment recorded completion of the already obtained founder
**NO-GO** decision and this authorized administrative reconciliation. It did
not record a new founder decision. At that baseline its issue stayed open until
the amended source merged and was separately reconciled under
[the tracking workflow](GITHUB_TRACKING.md).
SPEC-021 and M4 remain open even when that administrative task is complete.

### Post-merge administrative status — 2026-10-06

[PR #220](https://github.com/jayanez/agent-braid/pull/220) merged at
`d53314706d065247735ae09d5deed60a1365bbbb` on `2026-10-06T13:10:55Z`.
[T014 #218](https://github.com/jayanez/agent-braid/issues/218) then closed at
`2026-10-06T13:12:34Z`. This updates the source/issue status; the original receipt
and Project counts above remain dated observations. It does not establish a new
Project readback or change the G4 NO-GO, SPEC-021's open parent or M4's open state.

The six audited personal repositories had **zero registered self-hosted
runners**. Existing local runner images are Linux ARM64 preparation, not active
registered runners or hosted x64 parity. Repository-level runners cannot form
an organization runner pool across personal repositories. Standard public Linux
jobs provide the obtained synthetic route; no new infrastructure was purchased.

Private lab snapshots retain their own verified, filtered provenance. One
SmartNotes `develop` allowlisted blob had changed; its new content was not read
or repinned. Recent private sync runs stopped at the billing gate with no runner
or steps. Their classification is **infrastructure not executed**. They do not
supply a successful source-window registration.

Real M3.5 capture still needs approved rights/privacy and protocol records,
an independent completeness control, and a successful private remote
registration at least 24 hours before each fixed 14-day UTC window. Two candidate
families cannot satisfy the proposed five-family evaluation threshold. No real
capture, labels, training, predictor benefit, scientific closure or M4 acceptance
is obtained by this delivery.

## Integration of subsequently merged planning

While the delivery PR was being validated, upstream [PR #219](https://github.com/jayanez/agent-braid/pull/219)
added the foundational portfolio, followed by [PR #221](https://github.com/jayanez/agent-braid/pull/221)
binding its six draft assurance records to public commit `cb31439`. This delivery
integrates those changes from `53faa6a` and preserves their assurance bindings.
README presents the six specifications as future targets with human review
pending. Their new tasks are outside the completed implementation tracks.

All inputs bound by the archived M3.5 and M4 experiment records still match the
integrated tree. Those records continue to describe `734feca`; the final
integrated candidate receives separate PR validation and hosted checks. Earlier
validation results do not certify that later candidate.

The [tracking extension receipt](../experiments/evidence/autonomous-delivery-2026-10-06/tracking-extension-receipt.json)
records an empty repository audit against the subsequently merged source
(27 specifications, 205 tasks and 12 milestones) and six custom Project status
updates: SPEC-022 through SPEC-027 now show **Review pending**, consistent with
their canonical mapping. Their existing issue creation and linking were performed
separately. Additional unmerged planning issues were visible in the Project, so
this extension asserts no global item counts. The original receipt remains a
dated observation; no new draft task or milestone was closed.

## README editorial references

The README was checked against the project's architecture, contracts, ADRs,
milestone decisions, operational guides, license map and actual CLI surfaces.
Current primary README references consulted for presentation included
[OpenAI Agents SDK](https://github.com/openai/openai-agents-python),
[Deep Agents](https://github.com/langchain-ai/deepagents),
[Microsoft Agent Framework](https://github.com/microsoft/agent-framework),
[OpenCode](https://github.com/anomalyco/opencode) and
[n8n](https://github.com/n8n-io/n8n). Their concise capability introductions,
first runnable examples, visual navigation and documentation paths informed the
layout. Agent Braid's capabilities and claims remain grounded in its own
implementation and evidence.
