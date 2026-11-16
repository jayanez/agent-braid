# Independent Codex review packet, SPEC-077 contract (2026-11-16)

Owner decision 2026-11-16: Codex, installed in the operator account on this Mac, is a
reviewer and verifier now. This review is read-only, runs no native harness attempt and
is not human review, founder approval or publication.

## How to run it

From the repository root of a checkout at the candidate commit:

```sh
"/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex" exec -s read-only -C "$PWD" \
  --output-schema specs/077-harness-mcp-readonly/review/codex-contract-20261116.schema.json \
  -o specs/077-harness-mcp-readonly/review/codex-contract-20261116.out.json \
  "$(cat specs/077-harness-mcp-readonly/review/codex-contract-20261116.md)"
```

Save the output unedited. The orchestrator records it as
`specs/077-harness-mcp-readonly/evidence/review/codex-contract-20261116.json` with the
command, the Codex version and the candidate commit (SPEC-077 T002), and triages each
finding.

## Candidate

- Repository `jayanez/agent-braid`, branch `develop`, at the merge commit of the PR
  that adds this packet.
- Scope (contract only, no implementation exists):
  - `specs/077-harness-mcp-readonly/spec.md`, `plan.md`, `research.md`, `tasks.md`,
    `validation-plan.md`
  - `specs/077-harness-mcp-readonly/contracts/harness-mcp-readonly.md`
  - `docs/adr/0043-harness-mcp-readonly-surface.md`
- Context to read, not to review: `agent_braid/harness_cli.py`,
  `agent_braid/plugin_mcp.py` (`tool_listing`, `Router`), `agent_braid/tooling_mcp.py`
  (`WorkspaceService.tools`, `capabilities`), `docs/adr/0031-portable-prompt-names.md`,
  `docs/adr/0038-analyze-work-request-contract.md`,
  `specs/060-portable-prompt-names/contracts/interface-delta.md`,
  `specs/049-harness-evaluation-learning/spec.md` (SC-008),
  `specs/050-braid-harness-adaptation/owner-decisions-20261113.md` (D3, D7).

## Prompt

You are an independent reviewer of the Agent Braid SPEC-077 contract at the checked-out
commit. Read the files in the "Candidate" section of
specs/077-harness-mcp-readonly/review/codex-contract-20261116.md and the context files
it names. Nothing is implemented; review the contract as a specification of code to be
written. Do not run any command that writes, launches a host or uses the network.

Review for:
1. Authority leaks: any path by which a tool result could carry
   executionAuthorization true, reach prepare/status/recover-inspect/inspect/validate/
   compare, a native launch, a grant, promotion, activation or a registry write.
2. Path safety: whether the resolution rule (workspace-relative, descriptor walk,
   O_NOFOLLOW on every segment, uniform refusal) is complete; gaps such as hard links,
   case-insensitive filesystems, Unicode normalization, the registered root itself
   being a link, or directory inputs for harness-evidence.
3. Argument design: whether the four input schemas and description texts are simple
   enough for a host model to author (compare issue #1343 / HELD-04), whether each
   description stays within 2,048 bytes, and any ambiguity a model could misread.
4. Bounds and refusals: whether the 65,536-byte cap, the no-truncation rule, the JSON
   Pointer rules and the value-redaction rules are well defined and testable; any
   refusal that could reveal host path existence.
5. Versioning: whether adding four plugin-owned tools is really additive under
   agent-braid-plugin/v0.2 while agent-braid-tooling/v0.2 stays unchanged, and
   whether anything forces agent-braid-tooling/v0.3 (issue #771).
6. Gate and claims: whether REQ-010 makes publication impossible without SPEC-049
   T014 results and a D7 outcome that keeps the harness open; overclaims in spec.md,
   research.md or ADR 0043; requirements without a testable scenario.

Do not propose new features or native runs. For each finding give an id, a severity
(critical, high, medium, low or info), the file and line, a concrete failure scenario
(input to wrong result) and a minimal fix. Then give a verdict: "no actionable
findings" or "findings". Answer only with JSON matching the output schema.

## What this review is not

It is not human review, founder approval, a host validity measurement (SPEC-077 T007)
or a publication decision (T008).
