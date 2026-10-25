# SPEC-060 research record

This record reuses the [SPEC-054 research](../054-plugin-surface-naming/research.md)
(sources M1-M16, S1-S7, A1-A11, X1-X10, V1-V6, P1-P4 and its conclusions) without
repeating it. Labels follow SPEC-054: **N** normative, **C** convention or
guidance, **O** observed product behavior or repository fact, **D** owner decision.
Quotes are verbatim and at most 15 words. Sources below were accessed on 2026-10-25.
The reused host facts were established on 2026-10-24 and have not been re-observed.

## Reused facts that decide this specification

- A5 (Claude Code): "Claude Code lists each MCP prompt as `/servername:promptname (MCP)`." For a
  portable server under key `agent-braid` the current names therefore display as
  `/agent-braid:agent-braid-analyze (MCP)`; the unprefixed names display as
  `/agent-braid:analyze (MCP)` (inferred, T009 observes it).
- X7 (Codex): MCP prompts are not supported, so the portable prompts change nothing in Codex.
- A3 and the SPEC-054 plugin result: the native plugin's skills are `/agent-braid:analyze`,
  `plan`, `evidence`, which equals the unprefixed prompt form (collision caveat, OD-5).
- M9/M10: prompts are user-controlled and exposed as slash commands, like skills.
- M11: the MCP specification states no prompt-name character or length rule, so the
  unprefixed names are valid.

## New repository facts (O, read from `origin/develop` at 8d24c6f5)

| # | Fact | Source file | Use |
|---|---|---|---|
| R1 | `SCHEMA_VERSION = "agent-braid-tooling/v0.1"` is stamped on envelopes (line ~432), provenance (~442), `capabilities()` (~462) and the tool `outputSchema` const (~603) | `agent_braid/tooling_mcp.py` | Scope of the version change |
| R2 | The three prompts come from one dict, `_PROMPT_TEXT`; `list_prompts` and `get_prompt` derive from it; `capabilities()` hard-codes the same three names | `agent_braid/tooling_mcp.py` (~564, ~465, ~682) | Single registry design |
| R3 | The plugin overrides only top-level `schemaVersion` of delegated envelopes with `agent-braid-plugin/v0.2` and pops `prompts` from capabilities; the nested core `provenance.schemaVersion` and the capabilities `schemaVersion` keep the core value | `agent_braid/plugin_mcp.py` (~46, ~129) | Scope A would change plugin-visible bytes |
| R4 | The System One verifier requires `envelope['schemaVersion'] == tooling_mcp.SCHEMA_VERSION` | `agent_braid/system_one_verified_tooling.py` (~31) | A constant change propagates to it |
| R5 | Literal `agent-braid-tooling/v0.1` appears in four test modules (one live-envelope equality) and in frozen SPEC-046 evidence | `tests/test_tooling_*.py`, `specs/046-native-ai-plugins/evidence/` | Pinned tests; frozen evidence untouched |
| R6 | `tests/test_tooling_mcp.py` asserts the prompt set equals the three prefixed names | `tests/test_tooling_mcp.py` (~503) | Intentional change |
| R7 | The installer's default server name is `agent-braid`; host approvals are `mcp__<name>__*` and contain no prompt names | `agent_braid/tooling_install.py` (~281), `agent_braid/tooling_hosts.py` (~648) | Installed hosts unchanged; default-key display |
| R8 | The legacy skill names `agent-braid-*` are listed in `tooling_assets.py` and `tooling_hosts.py`; the evaluation fixture file `prompts.json` holds six evaluation prompts that are unrelated to MCP prompts | `agent_braid/tooling_assets.py`, `agent_braid/tooling_hosts.py`, `examples/tooling/prompts.json` | Do not confuse; unchanged |
| R9 | Python package and `serverInfo.version` are `0.1.0a1`; the plugin builder vendors a wheel of the same source under its own plugin version | `pyproject.toml`, `agent_braid/__init__.py`, `scripts/build_native_plugin.py` | Release carrier |
| R10 | The alpha.4 plugin documentation records tag `agent-braid--v0.1.0-alpha.4` as published | `docs/tooling/NATIVE_PLUGINS.md` | Plugin release already out; none required here |
| R11 | SPEC-055 and SPEC-056 have no directories; the milestone index records them as working numbers cited in the #683 squash message | `docs/development/SPEC_MILESTONE_INDEX.md` | Numbering decision OD-7 |

## Deprecation-window precedents (new)

| # | Source | Quote or paraphrase | Label | Use |
|---|---|---|---|---|
| W1 | https://peps.python.org/pep-0387/ | "Wait for the warning to appear in at least two minor Python versions" | C | Release-counted windows; N = 2 |
| W2 | same | the warning message "should include the release the incompatibility is expect[ed]" (paraphrase) | C | Marking names the removal contract |
| W3 | same | deprecation periods are counted in releases, not time, with removal needing notice between consecutive releases (paraphrase) | C | No silent removal |
| W4 | https://kubernetes.io/docs/reference/using-api/deprecation-policy/ | "API elements may only be removed by incrementing the version of the API group." | C | Removal only in a new versioned contract (v0.3) |
| W5 | same, rule 4a | alpha API versions "may be removed in any release without prior deprecation notice" | C | An alpha contract may legally drop aliases at once; the window is a courtesy chosen by D3, which bounds its cost |
| W6 | SPEC-054 naming policy, change control | "Deprecated aliases SHALL NOT be published on a surface where they would recreate a duplicate invocation" | D | The rule this specification narrowly excepts |

## Findings

1. The version change can be scoped to the surface because the envelope shape does
   not change (R1, R3, R4, R5). Scope B keeps plugin, verifier, fixtures and four
   test modules unchanged; scope A trades that for a single stamp.
2. Aliases are a deliberate exception to W6; W1/W4 give a precedent for a
   release-counted window removed by a new version, and W5 shows an alpha could
   skip the window, which is why the window is an owner decision (OD-2).
3. The unprefixed prompt form equals the native plugin skill form (A3), so a
   user with both surfaces under the default key can see the same slash name twice
   (OD-5). Neither the repository nor the sources establish how Claude Code
   disambiguates them; T009 observes it.
4. Prompt traffic is not counted (SPEC-040 interface, SPEC-047 enum), so non-use of
   the aliases cannot be shown; the window must be release-based.

## Limits

Host display forms for the new names are inferred from the documentation of the
`/servername:promptname (MCP)` rule, not observed. No downstream consumer of the
portable prompt names other than the repository itself is known, and the repository
cannot enumerate external consumers. The package distribution channel for portable
users is not established by the repository record (R9). Context7 was not used: no
library API documentation was needed beyond the SPEC-054 record.
