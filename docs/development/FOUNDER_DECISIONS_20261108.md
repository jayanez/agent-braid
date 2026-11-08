# Founder decisions — 2026-11-08

Successor of [FOUNDER_DECISIONS_20261107.md](FOUNDER_DECISIONS_20261107.md). The
owner (jayanez, founder) gave these decisions interactively in a Claude Code
planning session for the Braid Lightning track; each question offered options,
consequences and a recommendation, and the owner chose the recommended option.
The transcript is not stored. These are direction and governance decisions, not
scientific findings or acceptance of any feature.

Program decisions L1–L5 (optimizer on the host subscription, first target the
SPEC-069 guidance, weight RL deferred, the name "Braid Lightning", full
specification of BL now) are recorded in
[the BL program](../../specs/070-braid-lightning-foundations/program.md).

1. **ADR 0039 accepted** — Braid Lightning boundary: advisory only, subscription
   route with extra cash spend EUR 0, no execution or grants, human-only
   promotion, verifiable rewards without LLM judges; the "no fine-tuning"
   statements of SPEC-034 to SPEC-037 are scoped to forecasting.
2. **ADR 0040 accepted** (founder, license boundary) — adapted MIT code from
   microsoft/agent-lightning in AGPL modules with retained license and per-file
   notices; standard-library core.
3. **ADR 0041 accepted; ADR 0042 stays proposed and deferred** — content-bearing
   traces only with `redacted` consent (effective with SPEC-074); local GPU weight
   training waits for a separate go/no-go.
4. **SPEC-071 OD-1** — the rollout runner may accept `CLAUDE_CODE_OAUTH_TOKEN` (and
   the OpenCode equivalent) read from the environment only and never written; any
   `*_API_KEY` stays refused.

SPEC-070 T001 (owner review of the program, spec, ADRs and configuration
contract) is complete with these decisions. `human_review` of SPEC-070 remains
pending until a frozen candidate is reviewed.
