# Vendored third-party skills

Provenance trail for skills that did not originate in this repo — audit, not policy: what was
brought in, from where, at what commit, under what licence.

Source: <https://github.com/wdm0006/python-skills>, commit `954796b7fc28e342cf08f80b9a4a39414a419c7a`,
MIT licence. Vendored as individual folders (mirrored into both `.claude/skills/` and
`.agents/skills/`, matching how this repo already keeps the two in sync for the speckit skills).

`microsoft/skills` was evaluated and rejected wholesale for this repo: it is almost entirely
Azure/M365 SDK wrappers, and `agent_braid` has zero runtime dependencies by design
(`pyproject.toml`: `dependencies = []`) — nothing in that catalog applies.

| Skill | Source path | Why it's here |
|---|---|---|
| `code-quality` | `skills/python/code-quality` | Concrete, verified gap: no ruff/mypy config exists anywhere in the repo today, despite the Constitution's reproducibility/rigor claims (falsifiable, peer-reviewable claims per `CITATION.cff`, `RESEARCH.md`). |
| `documentation` | `skills/python/documentation` | Concrete, verified gap: no docs site (no mkdocs/sphinx) exists despite the explicit academic-reuse intent (`CITATION.cff`, split AGPL/CC-BY-SA licensing meant for citation). |
| `api-design` | `skills/python/api-design` | The classification API (`independent-candidate`/`ordered`/`conflicting`/`unknown`) is real public, citable surface — deprecation and error-handling discipline matters for reuse. |
| `testing-strategy` | `skills/python/testing-strategy` | **Caveat, confirmed with the maintainer**: this skill teaches pytest fixtures/parametrization and Hypothesis property-based testing. The repo today uses stdlib `unittest` (`python3 -m unittest discover`). Installed as-is; adopting pytest/Hypothesis as a **test-only** dependency (mirroring how `jsonschema` is already an accepted dev-only dependency) is a stack decision for the maintainer, not something this skill's presence implies on its own. |
| `cli-development` | `skills/python/cli-development` | **Caveat, confirmed with the maintainer**: this skill teaches Click/Typer. The repo's CLI (`agent_braid/cli.py`, entry point `agent-braid`) is confirmed stdlib `argparse`, by design (zero runtime dependencies). The CLI-*design* principles (subcommand structure, help text, exit codes) still transfer — apply them with `argparse`, not by adding Click/Typer as a runtime dependency. |
