# SPEC-054 T001: owner review packet

Prepared for the owner's review of the native plugin naming policy. This file
records no decision, creates no review record and does not freeze anything.
Labels follow [research.md](research.md): N normative, C convention,
O observed behavior, D owner decision.

## 1. What to read, in order

1. [contracts/naming-policy.md](contracts/naming-policy.md): the five principles,
   the per-surface rules (current value, policy value, basis) and the resulting
   invocations on each host. This is the object under review.
2. [research.md](research.md): every cited source with its quote, its label and
   how the policy uses it; the final section lists the limits.
3. [../../docs/adr/0030-native-plugin-surface-naming.md](../../docs/adr/0030-native-plugin-surface-naming.md):
   the decision, alternatives and consequences, and its narrowing of ADR 0024.
4. Optional: [spec.md](spec.md) (REQ-001, SC-001 define this review) and
   [plan.md](plan.md#human-review-and-unresolved-decisions).

## 2. Decisions as recorded

| ID | Recorded decision | Where |
|---|---|---|
| D1 | The plugin MCP server stops publishing MCP prompts; skills are the only invocation surface. | spec.md |
| D2 | Plugin skills drop the `agent-braid-` prefix inside the plugin namespace. | spec.md |
| D3 | Portable server keeps `agent-braid-tooling/v0.1`; unprefixed prompt names are only the target of a future versioned contract. | spec.md |
| D4 | MCP tool names stay unchanged; only display metadata may be added. | spec.md |
| D5 | No tool or server `title` metadata in alpha.4. | plan.md |
| D6 | alpha.4 does not bundle SPEC-046 T016-T019. | plan.md |
| D7 | ADR 0030 is Accepted; it amends ADR 0024 for plugin packaging only. | plan.md, ADR |
| D8 | Remote GitHub tracking is created through the reviewed reconciliation workflow. | plan.md |

Note for the reviewer: spec.md still says "draft specification" and "proposed ADR
0030", and the policy contract says "draft contract", while the ADR header and
plan.md say Accepted. D1-D4 are described in spec.md as selections that are not ADR
adoption. Whether to align that wording is part of the review.

## 3. Status of the evidence

Merged into `develop` (verified with `gh pr view`):

- #684 policy, research and ADR 0030 (docs).
- #686 T008: plugin interface v0.2 and invocation docs.
- #687 T003, T007: plugin MCP prompts removed, `agent-braid-plugin/v0.2`.
- #688 T002, T004: unprefixed packaged skills and the name check.
- #690 T005, T006, T010: `0.1.0-alpha.4` candidate.

Not observed, only inferred or sourced from documentation and code (research.md
Limits):

- The Codex qualified skill name `agent-braid:analyze` is inferred from Codex
  source (X4), not observed.
- Codex lacking MCP prompt support rests on an open upstream issue (X7,
  openai/codex#5059), not on a test of this candidate.
- Claude Code behavior comes from documentation (A1-A8) plus the owner's observed
  `0.1.0-alpha.3` display; the alpha.4 display is not observed.
- Inferred: a portable server registered under key `agent-braid` still shows
  `/agent-braid:agent-braid-analyze (MCP)`.
- Hosts may change behavior after the cited revisions.

Pending:

- T001 (this review), T009 native observation in Codex and Claude Code user
  profiles, including update from alpha.3 (blocked on owner-run sessions).
- Release: tag, build and `plugin-dist` publication are separate owner decisions.

## 4. Questions for the owner

1. Verdict on the policy and research record: accept, or changes-requested (name
   the rules)?
2. Is the N / C / O / D labelling adequate? In particular, are rules that rest on
   C or O only (server key equals plugin name; no plugin prompts; skill prefix
   drop) acceptable without a normative source, given that no fetched page
   states a preference between prompts and skills?
3. Do tool names stay kebab-case (`analyze-work`, `plugin-status`, ...)? The
   research notes that snake_case is more common (P4, V5) but not required, and
   that a rename changes the frozen SPEC-047 `mcp` enum and permission rules.
4. Are the portable server's future v0.2 target prompt names `analyze`, `plan`,
   `evidence` right, knowing the timing and alias window are unscheduled?
5. Should the draft/proposed wording in spec.md and the policy contract be
   updated to match the Accepted ADR?

## 5. What a decision does and does not authorize

- Accepting T001 confirms that the policy and research record are adequate for
  REQ-001/SC-001. It does not release, tag, build for or publish to `plugin-dist`.
- It does not replace T009 native observation or the separate release decision.
- It makes no scientific claim; the work is engineering only and changes no
  effects, authority, analysis results or evidence.
- Approval binds the exact frozen commit that is reviewed. Any later change to the
  policy, research or ADR needs a new review. Freezing happens later, from a clean
  merged candidate, and is not done by this packet.
