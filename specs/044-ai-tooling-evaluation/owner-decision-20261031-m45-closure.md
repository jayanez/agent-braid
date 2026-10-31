<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Owner decision 2026-10-31: observational native receipts and M4.5 closure

**Date:** 2026-10-31.
**Decider:** Juan Antonio Yáñez García (founder). This file is an agent-recorded
transcription of the founder's chat answer relayed by the coordinator session; it is
not a signature and creates no authority beyond the answer itself.
**Question:** whether the owner's real Claude Code transcripts may serve as native
evidence for milestone 19 (M4.5) and what happens to the rest.
**Answer (verbatim):** "Sí y cerrar el resto".

## Effect of the decision

1. The owner's real host sessions are accepted as **observational** native evidence
   for SPEC-041 and SPEC-043.
2. Their validation plans are amended (below and in each spec's `validation-plan.md`).
3. Tasks that the receipts cover are ticked. Every other open M4.5 task moves to a
   "Deferred" milestone with the reopen criteria listed here.

The decision does **not** alter the constitution, `native-observation-contract-v1.md`
(unchanged; the new class is additive and does not satisfy its T002/T017 gates), the
frozen SPEC-060 files, any registered or preregistered protocol, or any frozen
candidate.

## Amendment: evidence class "observational native receipt"

**Definition.** A derived receipt extracted read-only from real host sessions that the
owner ran for their own work: `~/.claude/projects` (Claude Code) and
`~/.codex/sessions` (Codex). Extraction uses the minimal read-only script
[`extract_observational_receipts.py`](../041-ai-tooling-skills/evidence/extract_observational_receipts.py)
(SPEC-053's adapter is blocked by its G0 gate and not implemented). Receipts keep only
skill and MCP tool names, timestamps, counts, plugin versions read from transcript
paths or tool envelopes, outcomes (`ok`, `refused`, `error`), SHA-256 digests of
loaded skill instructions and 12-hex session hashes. No prompt, tool input, assistant
text, working directory or project name is retained or committed.

**Mapping to the three levels of `native-observation-contract-v1`.**

| Level | What an observational receipt can show | Source in a transcript |
|---|---|---|
| C1 discovery | The skill (and the plugin MCP server instructions) were present in the model context. It is *listed-in-context*, not a process-level effective inventory, and it cannot prove the listing preceded prompt submission. | `skill_listing` and `mcp_instructions_delta` attachments (Claude Code); skill list in the session context (Codex) |
| C2 instructions loaded | The same session loaded that skill's instructions: path-derived package version and a content digest. | The `Base directory for this skill` message tied to the `Skill` tool call |
| C3 observed use | A skill invocation or MCP tool call and its result in that session, including refusals. | `Skill` / `mcp__plugin_agent-braid_agent-braid__*` tool calls and results |

Each level carries `observed` or `not-observed`; absent evidence is never success.

**What this class does NOT prove.**

- It is **not preregistered**: no population, prompts, arms, caps or stopping rule were
  fixed beforehand, and sessions are the owner's own work, so there is selection and
  no counterbalancing. It supports no comparison, utility or speed-up claim.
- It is **not tied to the frozen candidate**. Plugin versions seen are
  `0.1.0-alpha.2`/`.3`/`.4` (skill cache paths) and `candidateVersion 0.1.0a1` (tool
  envelopes). A claim is bound to a version only where the transcript shows it;
  otherwise the version is recorded as `unavailable`.
- It has **no refusal counterpart unless one was observed**. Observed MCP refusals
  (`status: refused`) are recorded as such. No refusal of a skill action is claimed.
- It does not establish an effective-inventory completeness claim, host-process
  identity, model identity, registration, clean-room reproduction, consent, human
  evaluation or founder acceptance of the frozen candidate.
- Counts are conservative: tool calls and skill loads are deduplicated by tool-use id (resumed
  sessions repeat history) and counted only when a result was recorded, so they are
  lower than raw text matches of the skill or tool names.
- Codex: skills appear in system/developer context in 8 sessions; no Codex skill or MCP use is
  observed.

## Receipts

| File | Content |
|---|---|
| [`041/evidence/observational-receipts-20261031.json`](../041-ai-tooling-skills/evidence/observational-receipts-20261031.json) | C1/C2/C3 per skill and MCP tool, per host |
| [`043/evidence/observational-journeys-20261031.json`](../043-ai-tooling-journey/evidence/observational-journeys-20261031.json) | per-session ordered skill/tool sequences with outcomes (hashed session ids) |
| `tests/test_observational_receipts.py` | synthetic controls: levels, outcomes, deduplication, no private content emitted |

Summary (Claude Code, scan on 2026-10-31, 2,880 transcript files, 622 with Agent Braid
events): all six skills listed in context in 188 sessions; instructions loaded (deduplicated by tool-use id) and
skill invoked for `analyze` (3), `plan` (4), `setup` (4); `execute`, `recover`,
`evidence` never loaded or used. MCP calls with results: `workspaces` 27,
`analyze-work` 24 (18 ok, 6 refused), `plugin-status` 20, `analyze` 7 (6 ok, 1
refused), `prepare` 6; first seen 2026-10-17, last 2026-10-27. Codex: six skills listed
in context in 8 sessions; no use.

## Sources consulted

Per the owner's standing instruction of 2026-10-31 and `docs/development/REAL_USE_EVIDENCE.md`
(coordinator policy, same date), every source below was queried read-only; the
receipt records numbers only (`localStores` in the SPEC-041 receipt).

| Source | Result |
|---|---|
| Claude Code transcripts | observations, above |
| Codex sessions | skills listed in context only; no use |
| Local technical telemetry (SPEC-047, 30-day window) | 19 daily-aggregate calls: MCP `analyze-work` 3 ok / 8 refused, `analyze` 1 refused, `execute` 1 refused (2026-10-16, no skill involved); CLI `analyze` 2 ok, `analyze-git` 2 ok / 2 refused. No skill-level data, so it cannot cover C1/C2 |
| Evidence, coordination and identity stores | present (133,998 / 15 / 1 files; modified 2025-12-05 to 2026-10-17); development evidence from earlier tracks, not examined as usage; 2 unreadable files |
| Runtime state | 3 files (2026-10-14 to 2026-10-15), not usage observations |
| Plugin workspace registry and results | 3 configured workspaces; 0 result files |

The MCP `execute` refusal is an observed refusal at the tool level only; it does not
cover SPEC-041 T004, which concerns the `execute` skill.

## Task mapping

Ticked only where the receipts cover the task. An independent review found T001 and T003 not covered; they are Deferred below:

| Task | Result | Receipt coverage and limits |
|---|---|---|
| SPEC-041 T002 | **Ticked** | `analyze`: C1, C2 (3 loads with digests, alpha.3/.4), C3 (3 invocations; MCP `analyze-work`/`analyze` with ok and refused outcomes). The explanation-quality clauses are content this class cannot observe and are not evidenced |
| SPEC-047 T010 | **Ticked** | Owner acceptance disposition, as relayed by the coordinator; not derived from receipts |

Deferred (not covered):

| Task | Why not covered | Reopen criteria |
|---|---|---|
| SPEC-041 T001 | only discovery observed: five skills (plus `setup`) listed in context in Claude Code (188 sessions) and Codex (8), but `execute`, `recover`, `evidence` never loaded and listing versions unreadable | all five skills loaded at recorded versions, per `procedure_portable_bundle` |
| SPEC-041 T003 `plan` | skill loaded and invoked (4), but no `prepare` after it in the same session and no way to observe the order/missing-authority disclosure | one session with `plan` skill, `prepare`, and the disclosed order and missing authority |
| SPEC-041 T004 `execute` | skill never loaded or used | C1–C3 receipts for `execute` on a granted exact batch, with a refusal counterpart for a wrong/expired grant |
| SPEC-041 T005 `recover` | never loaded or used | C1–C3 receipts for an interrupted or mismatched run, with a refusal counterpart |
| SPEC-041 T006 `evidence` | never loaded or used | C1–C3 receipts for verified, failed and inconclusive records |
| SPEC-041 T007 | no unavailable-MCP/skill/host case observed | an observed missing-capability session with a read-only fallback |
| SPEC-041 T008 | no adversarial instruction observed | observed untrusted text asking for grants/secrets/false success, with deterministic refusal |
| SPEC-041 T009, T010 | depend on T004–T008; need a frozen candidate bound to the evidence and a human decision on it | T004–T008 closed, then candidate freeze, quick/PR gates and decision |
| SPEC-043 T001 | no execute, recover or export step observed; install-to-plan fragments only | one session (or an owned synthetic journey) covering install, analysis, plan, grant refusal, execute, verify, recovery and export |
| SPEC-043 T003 | plan skill loaded, but no receipt of the explanation of advisory order and missing authority before execution | observed plan session with `prepare`, the order and the exact missing authority explained, then refused execution |
| SPEC-043 T008 | `setup` and `plugin-status` observed in Claude Code only; no diagnostics, raw-evidence access or unsupported-rendering explanation, and no Codex | both hosts show onboarding, diagnostics, raw-evidence access and rendering fallback |
| SPEC-043 T009, T010 | depend on T001–T008 | T001–T008 closed, then gates, freeze and decision |
| SPEC-044 T001, T002, T005–T010, T017, T018 (#451, #452, #455–#460, #595, #596) | the preregistered comparison, Codex coverage and the contract correction need the owner's registered cohort; observational receipts are not a substitute | a new owner decision to fund the registered evaluation; T002 additionally needs C1–C3 in both hosts, T017 an owner-reviewed correction of the contract |
| SPEC-046 T014, T015 (#551, #552) | external OpenAI/Anthropic submissions | an owner decision to submit and the external requirement being met |
| SPEC-060 T011 (#771) | alias removal under `agent-braid-tooling/v0.3` | every removal criterion in SPEC-060, two published window releases and an owner removal decision; deadline **2027-04-25**; frozen SPEC-060 files untouched |

Parent issues follow their children. Reopen any deferred item through a new owner
decision, never by reading these receipts as acceptance.
