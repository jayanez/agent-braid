# Radar-to-adoption pathline

## Purpose and scope

Agent Braid receives a weekly scientific and technology radar containing papers,
standards, product capabilities and market signals. This feature defines a
controlled path for deciding whether a signal represents a material, measurable
capability gain worth investigating or incorporating into Agent Braid.

The pathline is a governance and evidence feature. It does not integrate an SDK,
add a provider dependency, change AIM, change certificates or authorize execution.
The weekly radar remains read-only. A human-reviewed decision is required before a
candidate can create implementation work.

## Authorities

Clause zero and Articles 13, 14, 17, 19, 21, 23 and 25 govern claim discipline,
evidence, reproducibility, public communication and the separation of research
from execution. `GOVERNANCE.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`docs/strategy/ECOSYSTEM.md`, `docs/strategy/COMMUNITY.md`, ADR 0005, ADR 0008,
ADR 0009 and ADR 0011 are subordinate process and architecture authorities.

The radar remains a source-claim register. The adoption-track record is a separate
decision artifact and must not rewrite frozen radar snapshots.

## Requirements and acceptance scenarios

### REQ-001 — Every material signal has an explicit pathline

Given a radar entry, when it is considered for project work, then it must link to
an adoption track with a stable identifier, current stage, explicit owner,
affected artifacts, evidence plan and next decision. A radar entry alone must never create
an implementation task.

See SC-037.

### REQ-002 — Differential gain is falsifiable

Given a candidate track, when it advances beyond triage, then it must state the
current Agent Braid baseline, a comparable alternative, an observable capability
delta, a falsifiable hypothesis, a metric, a corpus or scenario and a result that
would invalidate the hypothesis. Marketing language alone is insufficient.

See SC-038.

### REQ-003 — Adoption stages have conservative gates

Given an adoption track, when its stage changes, then the record must satisfy the
entry and exit conditions for that stage. A negative or inconclusive spike may end
as `watch`, `rejected` or `research-only` without forcing a positive result.

See SC-039.

### REQ-004 — Provider evidence maps one-way into existing semantics

Given a technology candidate, when a spike or adapter is proposed, then it must
preserve identity, attempts, effects, dependencies, versions, hashes, provenance
and uncertainty while reusing AIM and the existing report contract. Missing or
unsupported information must become `unknown`, never an inferred absence.

See SC-040.

### REQ-005 — Adoption cannot silently change authority or execution

Given a track marked `adopted`, when it affects a public contract, runtime,
security boundary, dependency or scientific claim, then a separate Spec Kit
feature and applicable ADR/review must exist. An adopted track does not grant
execution, merge or publication authority.

See SC-041.

### REQ-006 — Historical radar and decisions remain auditable

Given a later source revision or technology version, when a track is revisited,
then the previous radar snapshot and decision remain immutable, the new source is
recorded separately and the track may be reopened or retired with a reason.

See SC-042.

## Pathline stages

The controlled stages are `observed`, `triaged`, `differentiation-hypothesis`,
`spike`, `specified`, `implemented`, `verified`, `decision` and `operated`.
Terminal decisions are `adopted`, `watch`, `rejected` and `research-only`.
Stage transitions are human decisions recorded in the adoption track; validators
check structure and prerequisites but never approve the transition.

## Initial track set

The first records seed, but do not adopt, the current signals:

- OpenAI Agents approval-aware evidence;
- MCP asynchronous task and state analysis;
- A2A conformance-backed task evidence;
- optional OpenTelemetry evidence transport;
- CoAgent/MTPO as a research comparator.

OpenAI Agents and MCP are the first implementation candidates only if their local
spikes demonstrate a measurable gain. A2A is gated on a selected protocol version
and conformance artifact. OpenTelemetry remains optional and experimental. CoAgent
remains research-only until artifact-level reproduction and comparison.

## Scientific boundaries and compatibility

The pathline records source claims, project hypotheses, finite evidence and human
decisions separately. It cannot establish market superiority, scientific novelty,
production safety, general confluence, contextual equivalence or a Yang–Baxter
result. It must preserve `unknown` and cannot convert guardrails, protocol
conformance or telemetry into permission to execute.

The first implementation changes no public AIM, certificate, assurance-level,
analysis-report or CLI contract. Public documentation remains English.

## Evidence and unresolved questions

Planned evidence is stored separately from obtained evidence. The first feature
only validates the pathline, schema, seeded records and negative cases. Provider
spikes, adapter correctness, external reproduction, scientific interpretation and
founder approval remain later gates.
