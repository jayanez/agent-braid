# Research: SPEC-077 read-only harness MCP surface

Engineering decisions with their evidence, alternatives and limits. No empirical
data is fitted here. SPEC-044 T005 (CLI vs MCP vs MCP+skills, 108 attempts) was
closed NOT_PLANNED, so no measured CLI-vs-MCP baseline exists; R1 and R7 rest on
the repository's contracts and the owner's counterfactual analysis of 2026-11-16.

## R1 Surface host and version

- **Decision (recommended, OD-1).** Plugin facade only. Four plugin-owned tools,
  additive under `agent-braid-plugin/v0.2`; their result payload is versioned
  separately as `agent-braid-harness-mcp/v0.1`. The portable
  `agent-braid-tooling/v0.2` surface is unchanged, so no `v0.3` is needed and issue
  #771 is not coupled.
- **Evidence.** `plugin_mcp.tool_listing` already adds plugin-owned tools
  (`plugin-status`, `workspaces`) beside delegated ones, and the portable listing
  already varies by mode (`analysis-only` vs `runtime-enabled` in
  `tooling_mcp.WorkspaceService.tools`). ADR 0030 item 4 treats unchanged tool names
  with new display data as additive. The SPEC-060 interface delta fixes the portable
  `v0.2` tool set as unchanged from `v0.1`, so adding tools there is a surface change.
  The plugin is the server all three hosts load (ADR 0037 for OpenCode).
- **Alternative.** Portable server too: needs `agent-braid-tooling/v0.3`. ADR 0031
  reserves `v0.3` for removing the three prompt aliases (#771), whose criteria need
  two releases carrying the marked aliases and an owner removal decision. A
  harness-driven `v0.3` before those criteria hold would either bump twice or force
  the alias removal early. If the owner wants the portable server, bundle both in
  one `v0.3` amendment once #771's criteria hold.
- **Limit.** "Additive" is a contract reading, not a host observation: installed
  verifiers and native evidence that count plugin tools (alpha.4 evidence records
  "five tools") change counts and must be updated with the implementation.

## R2 Argument design (lesson from #1343)

- **Decision.** Flat objects, `additionalProperties: false`, at most `workspaceId`,
  one path and one optional hash. The compact schema text and one example call sit in
  the tool description (2,048-byte cap, below ADR 0038's 1,500-token D12 cap).
- **Evidence.** #1343: on the SPEC-069 held-out set, Claude Code and OpenCode reach
  27/30 and Codex 24/30 first-attempt validity for `analyze-work`; HELD-04 fails every
  trial on every host with the same over-declared `read` signature. The failures sit
  in authored nested request bodies; a path string offers no such degree of freedom.
- **Alternative.** Schema delivered only through a resource or a skill: rejected in
  ADR 0038 (hosts do not reliably read resources; skill-only was the interim #1099).
- **Limit.** Simpler arguments do not guarantee validity; REQ-009 measures it.

## R3 Path resolution

- **Decision.** Workspace-relative POSIX path, resolved under the registered source
  root by a descriptor walk with `O_NOFOLLOW` on every segment. Missing, link,
  special file and outside-root cases return one identical refusal.
- **Evidence.** The CLI's `_read` uses `O_NOFOLLOW` on the final component only; a
  shell user chooses their own paths, a host model does not, so the MCP boundary is
  stricter. ADR 0038 refusal rule: a missing path and a path outside the roots return
  the same refusal.
- **Limit.** Races with a concurrent writer inside the user's own workspace are out
  of the threat model (same as the CLI).

## R4 Output bound

- **Decision (OD-3).** 65,536 serialized bytes; over the cap the call refuses with
  `output-too-large` and the observed counts. No truncation, no pagination in v0.1.
- **Evidence.** Inputs are already bounded (1 MiB record, 256 evidence files); an
  evidence listing of 256 files is about 50 KB. Host tool-output limits truncate
  silently near that order, which would hide entries without a marker.
- **Alternative.** Pagination with a cursor: more arguments, against R2.

## R5 Telemetry

- **Decision (OD-4).** SPEC-047 `OPERATIONS['mcp']` is a closed enum; unknown names
  are recorded as `other`. Add the four names in the same batch-schema change that
  adds harness CLI telemetry (track F of the HAR wave), so the schema bumps once.
- **Limit.** Until then, harness MCP calls are invisible as such in telemetry.

## R6 Held-out validity test

- **Decision.** New held-out set of 10 prompts (including at least two that ask for
  execution, promotion or a grant), frozen by SHA-256 before any run, 3 repetitions
  per host, the SPEC-069 automated driver (`scripts/spec069_native_runs.py`) adapted
  to score harness tool calls. Target per host: at least 8/10 prompts valid at the
  first attempt and 10/10 within one refusal-guided retry (OD-2).
- **Validity of a trial.** The model calls the intended tool with schema-valid
  arguments naming the intended file, or, for a forbidden-effect prompt, calls no
  harness tool for the effect and states the capability is absent.
- **Limit.** Three hosts, one model each; results are descriptive with Wilson 95%
  intervals, not a population claim.

## R7 Native execution excluded

- **Decision.** No launch, attempt or probe over MCP (owner, 2026-11-16).
- **Evidence.** The MCP server runs as the operator user and cannot `sudo` the
  root-owned SPEC-065 launcher; a launch from that context would change the
  environment hash bound by the qualification issuance; it would spend subscription
  quota; host tool approval is a host prompt, not an operator grant (ADR 0035).
