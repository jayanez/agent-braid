# Agent Braid contributor instructions

Read `CONSTITUTION.md` before normative, scientific or feature work. It is the sole
normative authority; `.specify/memory/constitution.md` is a byte-exact replica.
Follow `GOVERNANCE.md`, applicable ADRs, operational semantics and versioned
contracts. Evidence supports only its stated domain and observation boundary.
Feature specifications cannot override these sources. Public documentation is
English. Preserve the distinction between analogy, hypothesis, empirical evidence
and formal result. Do not present structural checks as scientific proof.

For Spec Kit work, read `docs/development/SPEC_KIT.md`. Both agents share the same
overrides; edit `.specify/templates/overrides/`, never generated skills. Run
`python3 scripts/validate_spec_kit.py` before feature work. The constitution command
only drafts proposals; amendments need a dedicated ADR, pull request, specific
review and founder approval. No command authorizes pushes, remote issue creation,
concurrent agents or autonomous delivery. Preserve unrelated user changes.

Use the proportional validation workflow in
`docs/development/VALIDATION_PROFILES.md`. During implementation run
`python3 scripts/validate_change.py --base develop --profile quick`; the planner
escalates sensitive or unknown paths. Run `--profile pr` once on a stable candidate.
Clean-room reproduction, evidence capture, human review and founder approval remain
separate boundary gates and are never implied by a passing profile. Install
dependencies only in isolated environments. Separate executed checks from pending
human, interactive or externally blocked checks.

<!-- context7 -->
Use Context7 MCP to fetch current documentation whenever the user asks about a library, framework, SDK, API, CLI tool, or cloud service -- even well-known ones like React, Next.js, Prisma, Express, Tailwind, Django, or Spring Boot. This includes API syntax, configuration, version migration, library-specific debugging, setup instructions, and CLI tool usage. Use even when you think you know the answer -- your training data may not reflect recent changes. Prefer this over web search for library docs.

Do not use for: refactoring, writing scripts from scratch, debugging business logic, code review, or general programming concepts.

## Steps

1. Always start with `resolve-library-id` using the library name and the user's question, unless the user provides an exact library ID in `/org/project` format
2. Pick the best match (ID format: `/org/project`) by: exact name match, description relevance, code snippet count, source reputation (High/Medium preferred), and benchmark score (higher is better). If results don't look right, try alternate names or queries (e.g., "next.js" not "nextjs", or rephrase the question). Use version-specific IDs when the user mentions a version
3. `query-docs` with the selected library ID and the user's full question (not single words)
4. Answer using the fetched docs
<!-- context7 -->

<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->

### Bounded CodeGraph workflow

- Start with `codegraph_explore` and a specific file or symbol; use `maxFiles`
  (CLI: `--max-files 2`) to bound the response. Treat returned current source as
  already read; follow exact elided symbol names only when needed.
- For a smaller slice, use `codegraph_node` (CLI: `codegraph node --file PATH
  --symbols-only`, or `--offset N --limit N`). Use `codegraph_search` for names,
  `codegraph_callers` / `codegraph_callees` for direct relationships, and
  `codegraph_impact` before changing shared symbols. `codegraph_files` provides
  indexed file structure; `codegraph_status` checks index health.
- For task context without source, use `codegraph context --no-code --max-nodes 8`.
  Use `codegraph affected PATH --json` to suggest affected tests; this does not
  replace the required validation profiles or establish complete test coverage.
- Pass this worktree's absolute `projectPath` when the MCP has no default project.
  The MCP watches changes; after a freshness warning or offline edits, run
  `codegraph sync` and check `codegraph status --json` before structural queries.
- Use direct reads/searches for unindexed documentation/configuration, missing
  results or explicit freshness failures. Resolution is best effort, not proof.
- Keep cross-call source deduplication disabled: context compaction and separate
  chats cannot guarantee that previously returned source remains available.
