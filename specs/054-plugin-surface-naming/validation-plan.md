# SPEC-054 validation procedures

Each procedure records the command, candidate and artifact hashes, environment,
expected and actual outcome, negative controls and limits. Missing native-host
observations stay pending.

## procedure_001

Review `contracts/naming-policy.md` against `research.md`: every rule has a
source label, no rule contradicts a cited normative source, and host
differences are explicit. Outcome: owner review record; no automated check
substitutes for it.

## procedure_002

Build the plugin in a temporary directory and assert plugin, marketplace and
server-key names equal `agent-braid` and the tool list equals the nine pinned
names. Negative controls: a mutated server key and a renamed tool fail.

## procedure_003

Connect an SDK client to the plugin server with two owned workspaces. Assert the
initialize result omits prompts, prompt listing returns nothing or is
unsupported, `get_prompt('agent-braid-analyze')` is refused with no side effect,
capabilities resources omit prompts and tool/resource tests still pass.

## procedure_004

Inspect the built package skills: directory equals frontmatter `name`; names
match `^[a-z0-9]+(-[a-z0-9]+)*$` and are at most 64 characters; bodies equal the
canonical bodies after applying only the declared substitutions; no
`agent-braid-(analyze|plan|evidence|execute|recover)` token remains; the
inventory records source hash, packaged hash and table. Negative control: an
unmapped prefixed reference fails the build.

## procedure_005

Run the existing portable MCP and legacy install suites; assert the three
`agent-braid-*` prompts, `agent-braid-tooling/v0.1` and the prefixed global skill
paths are unchanged.

## procedure_006

In owned fixtures, install an alpha.3 package with a v0.2 registry and results,
update to the candidate, then reinstall alpha.3. Assert registry and results
bytes survive both steps and listed skills and prompts match each version.
Review release notes for every removed and renamed invocation.

## procedure_007

With telemetry `local`, exercise each delegated tool and a prompt request;
assert operations stay within the SPEC-047 `mcp` enum, no prompt traffic is
counted and batch/store versions are unchanged.

## procedure_008

Search updated documentation and packaged skills for invocation names and
qualified tool ids; assert the policy forms and no claim of Codex MCP prompt
support.

## procedure_009

Owner-run native sessions in Codex and Claude Code user profiles: install or
update the source-bound candidate, list skills and MCP prompts, run the analyze
skill on a registered fixture, and record actual names, outcome, versions and
limits.
