# Contributing

For specification-driven work with Codex or Claude Code, follow the shared
[Spec Kit guide](docs/development/SPEC_KIT.md). Both environments use the same
normative controls; do not edit generated skills or the constitutional replica.

Thank you for helping turn Agent Braid into rigorous, useful infrastructure.

## Before contributing

Read:

1. [CONSTITUTION.md](CONSTITUTION.md)
2. [TERMINOLOGY.md](TERMINOLOGY.md)
3. [RESEARCH.md](RESEARCH.md) for empirical or mathematical work
4. [ARCHITECTURE.md](ARCHITECTURE.md) for implementation proposals

## Contribution paths

- semantic definitions and counterexamples;
- effect metadata and interoperability;
- concurrency and scheduling algorithms;
- Git/worktree fixtures;
- normalizers and observational equivalence;
- property-based and formal verification;
- benchmarks and reproducibility tooling;
- documentation and precise criticism.

## Required claim labels

Research-oriented contributions should label central claims as one of:

- `analogy`
- `hypothesis`
- `heuristic`
- `empirical`
- `exhaustive-finite`
- `formal`

If uncertain, choose the weaker label and explain what evidence would justify promotion.

## Pull requests

A pull request should include:

- the problem and intended observation boundary;
- constitutional articles affected;
- alternatives considered;
- tests, fixtures, or proof artifacts;
- assurance level before and after the change;
- known failure modes and counterexamples;
- compatibility and schema implications.

Do not combine a constitutional change with unrelated implementation work.

## Licensing of contributions

By submitting a contribution, you represent that you have the right to license
it and agree that it is provided under the license applicable to the material it
modifies:

- software, schemas, executable examples, and automation use `AGPL-3.0-only`;
- documentation and research use `CC-BY-SA-4.0`.

New files follow the default classification in [LICENSE](LICENSE). A pull request
that introduces a new artifact class must state its intended category. Do not
submit material under terms that are incompatible with the target license.
Contributions do not grant rights to use the project's marks beyond truthful
reference; see [TRADEMARKS.md](TRADEMARKS.md).

## Experiments

Experiments must follow [docs/experiments/PROTOCOL.md](docs/experiments/PROTOCOL.md). Generated traces containing secrets, proprietary code, personal information, or third-party confidential data must not be committed.

## Architecture decisions

Use `docs/adr/0000-template.md`. Accepted ADRs are immutable except for status and links to superseding decisions; corrections should be explicit.

## Local validation

During implementation, run the change-aware quick profile against the target branch:

```bash
python3 scripts/validate_change.py --base develop --profile quick
```

It always checks fast repository invariants and runs tests owned by the changed
paths. Normative, contract, scientific, supply-chain, validation-policy and unknown
paths automatically escalate to the sensitive profile. The plan is printed before
execution, including any deferred evidence boundary.

Once the candidate is stable, run the complete repository gate exactly once:

```bash
python3 scripts/validate_change.py --base develop --profile pr
```

Install development dependencies in an isolated environment. A passing profile is
an executable check, not evidence capture, clean-room reproduction, human review or
approval. Milestone, release, publication and scientific evidence procedures remain
explicit separate commands. See the
[validation profile guide](docs/development/VALIDATION_PROFILES.md) and
[laboratory](research/lab/README.md). Keep model results distinct from production
guarantees.

## Maintainer tooling

Optional. [xgrep](https://github.com/momokun7/xgrep) is an indexed code search
tool with an MCP server, configured per machine for the maintainer's editor. It
is not a dependency of this repository: nothing in `research/`, `schemas/` or
`scripts/` imports it, no validator or workflow invokes it, and a contributor
without it runs every check in this document unchanged.

It does not engage Article 22. That article governs an MCP surface Agent Braid
*exposes* as its mathematical laboratory; this is an MCP server the maintainer's
editor *consumes*, which creates no obligation on the algebra, no schema and no
runtime coupling. See [the constitution](CONSTITUTION.md).

Article 15 says declared metadata shall not be blindly trusted when verification
is possible, so what was verified is recorded here. Version 0.7.0, MIT, binary
`xg`. The release archive for `x86_64-unknown-linux-gnu` has SHA-256
`78fc6cb56cbd1052d2ed4fa8cf9899d240ffed7cbd9cc2879a127d2bbc1c0d6e`, and for
`aarch64-apple-darwin`
`186fc592c96e7b674dac95cb233d92b10f4b3c0e606b155ee6badaa37c976680`. Its manifest declares no
known network dependency — a bounded observation, not an impossibility: absent crate
names do not exclude `std::net` or a subprocess, and **what gets installed is the
prebuilt binary, whose bytes the manifest does not describe**, which is what the
pinned digests are for. Its `read_file` tool is confined to the configured root by
canonicalised prefix check — verified by requesting a path
outside the root and receiving a refusal. Its index is written under
`~/.cache/xgrep/`, not into the working tree, and it honours `.gitignore` **when
indexing** — which is not the same as being unable to read an ignored file. Its
`read_file` tool is bounded by `--root` alone and is **not** gitignore-filtered, so
`.env` and `traces/private/` are absent from search results and still readable by
name. This repository carries no `.claude/settings.json`, and therefore no
`mcp__<server>__read_file` deny rule, so `--root` is the only boundary here.

Measured limits, so no one reads more into the tool than it does. The one that
matters most is structural and has no remedy: **it indexes no path with a hidden
component** — not dot-directories and not dot-files, at any depth. Measured on this
tree: 187 tracked files, 63 with a hidden component, and xgrep indexes 122. So
`.github/workflows/validate.yml` — this repository's only CI, the validator every
contribution must pass — is invisible to it, and so are `.claude/skills/`,
`.agents/skills/` and `.gitignore` itself. Grep reads those; xgrep does not.

Second, for roughly thirty seconds after a file changes it answers from the
previous index while `index_status` still reports `"state": "fresh"`, so a
search run straight after an edit returns nothing for a symbol that exists and
gives no sign that it is guessing; its MCP tools take no freshness argument, and
only a rebuild (`build_index`, or `xg init`) closes that window.

A zero result from xgrep is therefore never evidence of absence, and grep
remains the authoritative search. Beyond that, its MCP `search` truncates twice
over — `max_results` defaults to 20 and a caller can raise it, while
`max_tokens` defaults to 4000 for MCP and keeps cutting after they do — and its
`find_definitions` covers Python, C# and TypeScript but not SQL.

The claim class for its usefulness here is `heuristic`: measured on this repository,
the advantage over ripgrep is a few milliseconds and result parity is exact once
case semantics are matched. The expectation that it earns more as the codebase
grows is an expectation, not a result.

Maturity, stated so the note does not read as current forever: xgrep is pre-1.0, has
a single author, 337 downloads on crates.io, and its last release was 2026-06-19.
**Revisit when a new release appears, or on 2026-12-19 if none has** — and if it is
still dormant then, the default action is to uninstall it: removing it costs nothing
and grep covers everything except `find_definitions`.

This note carries no assurance level, and deliberately: it describes
configuration outside the repository and is not load-bearing for any result
the repository publishes.

## Conduct

Disagreement is expected and valuable. Critique claims, definitions, evidence, and implementations—not people. Mathematical sophistication must be used to clarify, never to exclude or intimidate.
