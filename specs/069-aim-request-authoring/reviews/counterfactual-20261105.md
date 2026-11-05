# SPEC-069: Counterfactual analysis (2026-11-05)

Requested by the owner after the adversarial review and before commit, push or
PR. Performed by an independent read-only analyst asked to test the chosen
design against alternatives and falsified assumptions, not to hunt defects.
Owner decisions taken on the findings are D6 to D9 in `spec.md`.

| ID | Counterfactual | Verdict | Disposition |
|---|---|---|---|
| C3 | No `units` kind; does `units` raise quality? `analysis.py` ignores evidence `method`, so host-authored `aim` with declared `complete` coverage gets `independent-candidate`, while honest `units` gets `unknown`: the incentive moves to the less honest kind. | change | D7: declared-not-observed label (REQ-015); `units` kept for conflict detection, conditional on P3 |
| C6 | Stop at PR #1099. No baseline exists for the interim guidance before adding new public surface. | change | D6: phases P1/P2/P3, P3 only if the baseline misses D4 |
| C2 | No schema in `inputSchema`, or MCP resource. Claude Code defers MCP tool schemas until use, so the per-session token estimate does not apply there; other hosts unverified. | guard | D9 ablation arm; REQ-005 records eager vs on-use loading; schema kept only if it helps in at least one host |
| C7 | AIM changes soon. `analysis.py` hard-codes `0.2.0-draft`; a new `aimVersion` just to tighten would mean multi-version support. | change | D8: no new version now; runtime-looser cases go to the next AIM version |
| C8 | Tightening breaks external producers. Schema-looser divergences break no working request; validator tightening would. Probe: 4 AIM records in examples/tests, 0 disagreements. | keep, corrected | REQ-009/SC-009 forbid runtime tightening in this feature (D8) |
| C5 | Headless or non-interactive auth unavailable; sandbox denies keychain. | guard | REQ-013: credentials read outside the sandbox and injected; ordered fallback; billing stated; fake-host evidence labelled |
| C4 | Threshold met on fixed prompts but field use fails, or models change. | guard | D9 re-run at each release and on host/model change; REQ-012 field metric from telemetry |
| C1 | Generate one artifact from the other. Loses REQ-007 refusal control or adds a runtime dependency; batch checks not expressible. | keep | REQ-002 guard: reopen D1 if more than 15 divergences |

The analyst's probe outputs are summarized above; no repository file was
changed by the analysis.
