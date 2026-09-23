# Vendored third-party skills

Provenance trail for skills that did not originate in this repo — audit, not policy: what was
brought in, from where, at what commit, under what licence.

Source: <https://github.com/wdm0006/python-skills>, commit `954796b7fc28e342cf08f80b9a4a39414a419c7a`,
MIT licence; the full notice is in [LICENSES/python-skills-MIT.txt](../../LICENSES/python-skills-MIT.txt).
Vendored as individual folders (mirrored into both `.claude/skills/` and
`.agents/skills/`, matching how this repo already keeps the two in sync for the speckit skills).
The entry points for CLI, testing, code quality, and documentation are adapted to
this repository; Click/Typer and pytest material remains optional reference material.

`microsoft/skills` was evaluated and rejected wholesale for this repo: it is almost entirely
Azure/M365 SDK wrappers, and `agent_braid` has zero runtime dependencies by design
(`pyproject.toml`: `dependencies = []`) — nothing in that catalog applies.

| Skill | Source path | Why it's here |
|---|---|---|
| `code-quality` | `skills/python/code-quality` | Concrete, verified gap: no ruff/mypy config exists anywhere in the repo today, despite the Constitution's reproducibility/rigor claims (falsifiable, peer-reviewable claims per `CITATION.cff`, `RESEARCH.md`). |
| `documentation` | `skills/python/documentation` | Concrete, verified gap: no docs site (no mkdocs/sphinx) exists despite the explicit academic-reuse intent (`CITATION.cff`, split AGPL/CC-BY-SA licensing meant for citation). |
| `api-design` | `skills/python/api-design` | The classification API (`independent-candidate`/`ordered`/`conflicting`/`unknown`) is real public, citable surface — deprecation and error-handling discipline matters for reuse. |
| `testing-strategy` | `skills/python/testing-strategy` | The entry point uses the repo's `unittest` suite and CI command. Pytest and Hypothesis references are optional; adopting either as a test-only dependency is a separate stack decision. |
| `cli-development` | `skills/python/cli-development` | The entry point uses the repo's `argparse` CLI and zero-runtime-dependency policy. Click and Typer references remain available only for an explicitly chosen alternate stack. |

## NVIDIA catalog candidates (not vendored)

The current core has no NVIDIA runtime dependency. Reassess these official
skills when their corresponding integration or experiment is scoped:

- [NeMo Relay call instrumentation](https://github.com/NVIDIA/skills/blob/main/skills/nemo-relay-instrument-calls/skill-card.md) for a tool-call trace adapter.
- [NeMo Relay context isolation](https://github.com/NVIDIA/skills/blob/main/skills/nemo-relay-instrument-context-isolation/SKILL.md) for concurrent trace scopes.
- [cuOpt optimization formulation](https://github.com/NVIDIA/skills/blob/main/skills/cuopt-numerical-optimization-formulation/skill-card.md) for a bounded scheduling experiment.
