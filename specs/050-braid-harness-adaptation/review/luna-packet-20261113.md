# Independent Luna review packet, SPEC-050 offline portfolio (2026-11-13)

Authorized by owner decision D5 in [owner-decisions-20261113.md](../owner-decisions-20261113.md).
The owner runs this review with gpt-6-luna (Luna Latest) in Codex, outside this host,
because no Luna client is installed here. Do not install Codex on the laboratory host:
SPEC-048 qualification assumes it is absent.

## How to run it

1. In Codex, open `jayanez/agent-braid` at the commit named below. Read-only access is
   enough, and nothing needs to run natively.
2. Paste the prompt from the "Prompt" section.
3. Save the answer exactly as Luna returns it, then hand it to the orchestrator session.
   The orchestrator records it as
   `specs/050-braid-harness-adaptation/evidence/review/luna-20261113.json`, plus the raw
   text, and fixes confirmed findings in separate PRs.

## Candidate

- Repository `jayanez/agent-braid`, branch `develop`.
- Commit: the merge commit of the PR that adds this packet. The orchestrator names it
  when handing the packet over. If it is unknown, review `develop` at that PR's merge.
- Scope, about 5,700 lines:
  - `agent_braid/harness_components.py` (T002)
  - `agent_braid/harness_tools.py` (T004, offline portion)
  - `agent_braid/harness_skills.py` (T003)
  - `agent_braid/harness_hooks.py` (T005)
  - `agent_braid/harness_orchestration.py` (T006)
  - `agent_braid/harness_search.py` (T007, Apache-2.0 adaptation of google-research/harness2)
  - `agent_braid/harness_curation.py` (T008)
  - `agent_braid/harness_auto_promotion.py` (T009)
  - `agent_braid/harness_lifecycle.py` (T011)
  - `agent_braid/harness_advisory.py` (T010)
  - their `tests/test_harness_*.py` files, and `tests/test_harness_integration_portfolio.py` (T012)
- Contracts and reports: `specs/050-braid-harness-adaptation/contracts/interface.md`,
  `contracts/advisory.md`, `capability-report.md` and `evidence/t0*.json`.

## Prompt

```text
You are an independent reviewer of the Agent Braid SPEC-050 harness portfolio at the commit
given. Read the files listed in specs/050-braid-harness-adaptation/review/luna-packet-20261113.md
(scope section) and the contracts it names. Everything is offline and synthetic; nothing may
grant execution authority or reach an "active" profile.

Review for:
1. Correctness bugs and fail-open paths: any route where executionAuthorization becomes true,
   a profile/run reaches active, a refusal is skipped, or a tampered/stale/forged record is
   accepted.
2. Filesystem safety in harness_lifecycle.py: writes or deletes outside the caller root
   (symlinks, races within the stated threat model), non-atomic state/registry updates,
   incomplete uninstall/purge/recover.
3. Privacy: private payload fields leaking into reports, journals, receipts or advisory output.
4. Test adequacy: guards whose removal no test would detect; tests that pass vacuously.
5. Claims: statements in capability-report.md or evidence/t0*.json that the code or tests
   do not support (overclaims), and gaps the report omits.
6. License/provenance: harness_search.py Apache-2.0 notice and change list versus
   docs/development/THIRD_PARTY.md.

Do not propose new features or native runs. For each finding give: id, severity
(critical/high/medium/low/info), file:line, a concrete failure scenario (input -> wrong
result), and a minimal fix. Then a verdict: "no actionable findings" or the list. Answer as
JSON: {"commit": "...", "reviewer": "gpt-6-luna", "findings": [...], "verdict": "..."}.
```

## What this review is not

It is not human review, founder approval, native qualification or activation. Under owner
decision D5, a delta review follows the native evidence of the D2 wave.
