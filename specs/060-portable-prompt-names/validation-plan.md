# SPEC-060 validation procedures

Each procedure records the command, candidate and artifact hashes, environment,
expected and actual outcome, negative controls and limits. None has been run; this
specification change only plans them. Native-host observations stay pending.

## procedure_001

Connect an SDK client to the v0.2 portable server. Assert `prompts/list` contains
`analyze`, `plan`, `evidence`; `prompts/get` for each returns the exact v0.1 text
of its predecessor (compared against the byte strings in the contract); an unknown
name is refused with no side effect; a 16 KiB-plus argument map is refused. Negative
controls: a changed canonical text and a missing canonical name fail. The owner
review of the contract and ADR (T001) is separate and not substituted by tests.

## procedure_002

With the same client, assert the list order (canonical then aliases), that each
alias description begins with the deprecation marker naming its replacement and
removal contract, that each alias returns the canonical text, and that the
capabilities resource lists the aliases under `deprecatedPrompts` only. Negative
controls: an unmarked alias and an alias under `prompts` fail.

## procedure_003

Run every tool and read every resource on identical immutable inputs against the
v0.1 candidate commit and the v0.2 candidate (two checkouts or recorded goldens).
Assert envelopes, output schemas and provenance are byte-equal and that the
capabilities resource reports `schemaVersion` v0.2 and `envelopeSchemaVersion`
v0.1. Negative control: a v0.2 stamp on an envelope fails under scope B (inverted
if the owner selects scope A).

## procedure_004

Connect an SDK client to the plugin server with two owned workspaces. Assert the
initialize result omits the prompts capability, listing returns nothing or is
unsupported, requests for a canonical name and for an alias are refused without
side effects, each per-workspace capabilities resource lacks `prompts`,
`deprecatedPrompts` and `envelopeSchemaVersion` and equals the alpha.4 golden
bytes, and plugin tool envelopes equal alpha.4 golden envelopes.

## procedure_005

Run the existing telemetry, legacy install, host configuration, plugin and System
One verifier suites; record which assertions changed and why (only prompt and
capabilities expectations). With telemetry `local`, list and get prompts (canonical
and alias) and assert no operation is recorded and batch/store versions are
unchanged. Compare a `tooling install` preview with the v0.1 preview byte for byte.

## procedure_006

In owned fixtures, write a host configuration with the v0.1 installer, install the
v0.2 package, start the server from that configuration and request both name sets;
reinstall the earlier package and request both sets again (old names resolve, new
names refused). Assert the configuration and result roots are byte-identical across
both steps. Limit: fixtures only; not a native host.

## procedure_007

Walk the removal criterion of the contract against a hypothetical removal with
each criterion missing in turn (release count, release-note text, owner decision,
repository search, installer/plugin references) and confirm each blocks the
removal. Run the repository search for the alias names and list the permitted
residual references. Executed for real only when T011 is authorized.

## procedure_008

Review the release-readiness record: package version, contract versions, changed
and unchanged surfaces, migration and rollback notes, plugin impact statement and
the explicit statement that no release, tag or publication occurred. The
`--profile pr` receipt is attached by T010.

## procedure_009

Search the updated documentation for prompt names and invocation forms: unprefixed
names primary, every `agent-braid-*` prompt mention marked deprecated or
historical, collision caveat present, no claim that Codex displays MCP prompts or
that the plugin publishes prompts.

## procedure_010

Owner-run or separately authorized Claude Code session: register the source-bound
candidate as a portable server under the default key, list slash commands, record
the names; repeat with the native plugin installed; record whether the two
`/agent-braid:analyze` entries are distinguishable and whether the aliases appear.
Record that Codex lists no MCP prompts. Include versions, platform and limits.

## procedure_011

Compare the final change set with the frozen inventory: no change under frozen
evidence paths, no SPEC-054 file, no accepted ADR, no SPEC-040/046 evidence; the
v0.1 contract text remains in SPEC-040. The check is a path comparison, not a
claim of semantic equivalence.
