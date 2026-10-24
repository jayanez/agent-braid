<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# SPEC-052 host-verification runbook (T023–T032)

Status: founder-run checklist. **Obtained evidence: none.** This file authorizes
no push, PR, version bump, release, grant, execution or paid spend, and records no
host outcome. Every command below is run by the founder on the founder's own
Claude Code host at EUR 0 additional spend (existing subscription only, see
[BUDGET](../../docs/tooling/BUDGET.md); no paid API key, credits or upgrade).
Negative, `fail` and `unobserved` outcomes are valid and must be recorded as such.
Never write a field you did not observe; leave it `null` and say why in `notes`.

Related: [tasks](tasks.md) T023–T032, [spec](spec.md) REQ-013 and REQ-016,
[validation plan](validation-plan.md), [quickstart](quickstart.md),
[recipe](../../docs/tooling/CLAUDE_WORKFLOWS.md).

## 0. Candidate package (prepared, engineering-only)

An engineering candidate was built outside the checkout from a clean tree. It is
**never a releasable identity** (the package carries `ENGINEERING-ONLY.json`,
`releasable: false`), shares the unchanged version string `0.1.0-alpha.3`, and
exists only for host verification.

| Field | Value |
| --- | --- |
| Source commit (clean, `sourceDirty: false`) | `9a85823de70362ab2e8ea37e557140127256bb49` |
| Plugin version string | `0.1.0-alpha.3` (unchanged; no bump) |
| Platform built | `macos-arm64` only |
| Build command | `scripts/build_native_plugin.py --output <out> --cache <cache> --platform macos-arm64 --include-workflows` run with a scratch Python 3.12 venv holding `build` |
| Package inventory hash (`sha256` of `plugins/agent-braid/package-inventory.json`) | `e850ccb872a9e87970fe075cc95664fb185c2093c1b571108b3c3b2993977f76` |
| `workflows/braid-gate.js` sha256 (equals the committed source file) | `d5c729953d750ff7a3ac3501bca3d038dbf0a00055fa113bcfb4b6a0d3a234b4` |
| `ENGINEERING-ONLY.json` sha256 | `5449fdf73c7944d6da36a93870018d32901f95f638bca2d6ffaf7c4730f51869` |
| Wheel sha256 | `8de854b5566ca02f63c6faf834bc8ff3521308a05518d8ce40a1030e951467a7` |
| Location at preparation time | `/private/tmp/claude-502/hv-kit-build/out` (scratch; may be cleaned by the OS) |
| `claude plugin validate <out>/plugins/agent-braid` (CLI 2.1.292) | `Validating plugin manifest: …/.claude-plugin/plugin.json` then `✔ Validation passed` |
| `claude plugin validate <out>` (marketplace) | `⚠ Found 1 warning: description: No marketplace description provided. Adding a description helps users understand what this marketplace offers` then `✔ Validation passed with warnings` |

`plugin validate` checks the manifest only. It is not a workflow, MCP or
host-behavior check and says nothing about HV-1 to HV-5.

**If the scratch directory is gone, or the founder prefers a fresh build**, rebuild
from a clean checkout of the same commit and compare the three hashes above
(the inventory hash can differ if build inputs differ; record the new value):

```bash
git -C <checkout> status --porcelain            # must be empty
python3.12 -m venv "$SCRATCH/venv" && "$SCRATCH/venv/bin/pip" install build
"$SCRATCH/venv/bin/python" <checkout>/scripts/build_native_plugin.py \
  --output "$SCRATCH/out" --cache "$SCRATCH/cache" \
  --platform macos-arm64 --include-workflows
shasum -a 256 "$SCRATCH/out/plugins/agent-braid/package-inventory.json" \
  "$SCRATCH/out/plugins/agent-braid/workflows/braid-gate.js"
```

The build downloads the pinned runtime archive and hash-locked wheels (no spend).
`$SCRATCH` and `<out>` must be outside the repository.

## 1. Rules for every run

- Run only in the scratch repository below. Never register or point the gate at a
  real project.
- Register **analysis-only** (no `--enable-runtime`, no `--grant-store`) except for
  the one deliberate runtime-enabled probe in HV-1, which uses a separate throwaway
  registry home and a scratch grant-store path that holds no grant.
- Do not run `grant-policy-run`, `execute-policy-run` or `recover-policy-run`. The
  gate returns `executionAuthorization: false`; approving a run in the host is not
  Agent Braid authority (ADR 0021).
- Save the full transcript of each probe (copy the terminal session or use the
  host's export) beside the JSON file. Evidence files go in
  `specs/052-claude-workflow-gate/evidence/` (the directory exists and holds only
  `corpus-comparison.json`, the T021 result; add the HV files beside it). Do not edit `tasks.md` boxes; the
  task checkbox change is a separate reviewed step after the evidence exists.
- Use the template of each section. `outcome` is exactly one of `pass`, `fail`,
  `unobserved`. Put the permission rule text you actually used verbatim; put raw
  host messages verbatim.
- If anything in this runbook differs from what the host does, record the
  difference in `notes`; do not "fix" the observation to match the runbook.

## 2. T023 — host prerequisites and scratch fixtures

Records: Claude Code version, platform, workflows setting, plugin version and
source commit, spend.

### 2.1 Host

```bash
claude --version
claude plugin list                      # note any already-installed agent-braid
```

Pick one host/version and keep it for all of HV-1..HV-5. Preparation noted CLI
`2.1.292` on macOS (arm64); the documentation read during planning described
workflows from v2.1.154 and v2.1.309. Whether `2.1.292` enables workflows, and how
the "workflows setting" is spelled, is **unverified**: look it up in that host's own
settings/docs, record the exact key and value, and if workflows are unavailable
record that and stop (HV items are then `unobserved`, not `fail`).

### 2.2 Load the candidate without touching an installed plugin

If an `agent-braid` plugin is already installed on this host, avoid mixing it with
the candidate. Preferred, session-scoped and non-persistent:

```bash
claude --plugin-dir "<out>/plugins/agent-braid"
```

If the host reports a name clash with the installed plugin, disable the installed
one for the test (`claude plugin disable agent-braid`) and re-enable it afterwards,
or use a separate `CLAUDE_CONFIG_DIR`. Record which method you used. The
alternative is a persistent local install (`claude plugin marketplace add "<out>"`
then `claude plugin install agent-braid@agent-braid`); if used, record it and
uninstall after the run.

### 2.3 Scratch fixture repository (owner-controlled, throwaway)

```bash
export FIX="$HOME/scratch/braid-hv-fixture"      # any new dir outside agent-braid
mkdir -p "$FIX" && cd "$FIX" && git init -q -b main
git config user.name hv && git config user.email hv@example.invalid
printf 'one\ntwo\nthree\n' > shared.txt; printf 'x\n' > a.txt; printf 'y\n' > b.txt
git add . && git commit -qm base
git branch agent/a main && git branch agent/b main && git branch agent/c main \
  && git branch agent/d main && git branch agent/conflict main
git switch -q agent/a  && printf 'x2\n' > a.txt && git commit -qam a
git switch -q agent/b  && printf 'y2\n' > b.txt && git commit -qam b
git switch -q agent/c  && printf 'c\n' > c.txt && git add c.txt && git commit -qm c
git switch -q agent/d  && printf 'd\n' > d.txt && git add d.txt && git commit -qm d
git switch -q agent/conflict && printf 'one\nTWO\nthree\n' > shared.txt && git commit -qam conflict
git switch -q main
git rev-parse main agent/a agent/b agent/c agent/d agent/conflict
```

This is only the minimal fixture for the probes (independent edits plus one
conflicting branch, which also helps HV-1/HV-4 get a non-trivial analyzer result).
The full fixture matrix (2, 4, 5 operations, deletion, equal-to-base, hardening
sentinels) is T030, which is blocked until T029 and is out of scope here.

### 2.4 Analysis-only registration (setup in analysis mode)

Use the packaged launcher. Preview, inspect the JSON and digest, then apply once
(analysis is the default; do not pass `--enable-runtime` or `--grant-store`):

```bash
L="<out>/plugins/agent-braid/launch"
"$L" plugin setup --home "$REG_ANALYSIS" --source-root "$FIX"             # preview
"$L" plugin setup --home "$REG_ANALYSIS" --source-root "$FIX" \
  --apply --preview-digest "<digest from the preview>"
"$L" plugin workspaces --home "$REG_ANALYSIS"                             # note WORKSPACE_ID
```

`$REG_ANALYSIS` is a new directory you choose (scratch registry home). Whether the
plugin MCP of the loaded candidate reads that home is **unverified**: call the MCP
`plugin-status` tool (or `"$L" plugin doctor`) and record the `registryHome` it
reports. If the MCP connection uses a different home, set up registration there
instead (or run the host with the environment the plugin documents) and record it.
Reconnect MCP after any registry change. Record `WORKSPACE_ID`.

### 2.5 Evidence: `evidence/host-prerequisites.json`

```json
{
  "task": "T023",
  "recordedAt": null,
  "operator": null,
  "claudeCode": { "version": null, "platform": null, "installMethod": null },
  "workflowsSetting": { "key": null, "value": null, "howLooked": null, "organizationDisabled": null },
  "pluginLoad": { "method": "plugin-dir | marketplace-install | other", "installedAgentBraidPresent": null, "handling": null },
  "candidate": {
    "pluginVersion": null,
    "sourceCommit": null,
    "packageInventorySha256": null,
    "braidGateJsSha256": null,
    "engineeringOnlyMarkerPresent": null,
    "pluginValidateOutput": null
  },
  "fixture": { "path": null, "base": null, "branches": {}, "gitVersion": null },
  "registration": { "mode": "analysis", "registryHome": null, "workspaceId": null, "pluginStatusRegistryHome": null },
  "spend": { "additionalEur": null, "paidApiOrCreditsOrUpgrade": null, "subscriptionOnly": null },
  "notes": null
}
```

**Pass criterion (T023 done):** every field above is filled from observation; spend
is 0 on the existing subscription. **No-go:** workflows unavailable on the host
(then record and stop; HV-1..HV-5 are `unobserved`).

## 3. Scratch workflow used by the probes

Two tiny ad-hoc workflows. Nothing here edits the repository; each ends with the
gate or a probe. Their exact authoring format is a host matter: confirm how this
host lets you author and start an ad-hoc workflow (user workflow directory, project
`.claude/workflows/`, or inline) and record it. The shape below follows the shipped
`braid-gate.js` (`export const meta`, `agent()`, `parallel()`, `workflow()`) and is
an **unverified sketch**; adapt names to what the host accepts and record changes.

### 3.1 `hv-ending.js` — minimal workflow that ends with the gate (HV-3 nested path)

```js
// Unverified sketch: the point is the final step, not the middle.
export const meta = {
  name: 'hv-ending',
  description: 'HV probe: read-only worktree-less workflow that ends with braid-gate',
  phases: [{ title: 'Probe' }, { title: 'Gate' }],
};
const args = { base: 'main', sources: ['agent/a', 'agent/b'], workspaceId: 'WORKSPACE_ID' };
phase('Probe');
// (no agents edit anything; the fixture branches already contain the committed work)
phase('Gate');
return await workflow('agent-braid:braid-gate', args);  // HV-3: name form is what is tested
```

If `agent-braid:braid-gate` does not resolve, also try the bare name `braid-gate`
and any plugin-namespaced form the host's own error or listing suggests; record
every name tried with its raw result.

### 3.2 Direct invocation (HV-3 direct path)

In the host session, with the candidate loaded and the registry from §2.4:

```
/agent-braid:braid-gate
```

with arguments `{"base":"main","sources":["agent/a","agent/b"],"workspaceId":"<WORKSPACE_ID>"}`
passed however the host passes workflow arguments (the slash-path argument format
is itself unverified; record what worked).

## 4. REQ-016 host permission allowlist — exact command templates

The gate is designed to run its agents under a host permission rule set that allows
only the items below. The rule **syntax** is host-specific and **unverified**: the
JSON/`--allowedTools` shapes in §4.3 are candidates to try, not a known-good
configuration. For each item record whether the host can express it narrowly
(exact or subcommand-level match), the verbatim rule you used and the observed
effect. A prefix rule for `git` or for the launcher binary is **insufficient** and
must not be used as a stand-in.

### 4.1 MCP path (primary)

Plugin tools, and only these four:

| Item | Template |
| --- | --- |
| MCP tools | `workspaces`, `analyze-work`, `analyze`, `prepare` (tool names as the host actually exposes them, e.g. `mcp__plugin_agent-braid_agent-braid__<tool>`; record the exact visible names) |
| Never allowed | `execute`, `recover`, `verify`, `status`, and any launcher/Bash rule matching the launcher binary as a whole |

Read-only Git, one rule per subcommand, each with the full hardened prefix the
workflow emits (read the exact prefix from `workflows/braid-gate.js`, constant
section; do not retype it from memory):

- `git … version`
- `git … rev-parse --show-toplevel`
- `git … rev-parse --path-format=absolute --git-common-dir`
- `git … rev-list -n 1 --end-of-options <rev>`
- `git … cat-file -e <object>`
- `git … merge-base --is-ancestor <a> <b>`
- `git … for-each-ref`
- `git … count-objects -v`
- `git … hash-object --stdin`
- baseline only, against the scratch directory only: `git … init --bare --template=` and `git … merge-tree --write-tree …`

Scratch (the only writes; temp directory outside the repository):

- create: `mktemp -d "${TMPDIR:-/tmp}/braid-gate.XXXXXXXX"` (exact command)
- remove: `rm -rf -- "<path>"` where `<path>` is `braid-gate.` + 8 alphanumerics directly under `TMPDIR` (or `/tmp`); the agent checks the pattern first

A host that cannot express the last two narrowly makes the baseline phase
unavailable (a recorded no-go), not unhardened.

### 4.2 Constrained-CLI fallback (only if HV-1 shows MCP tools are not visible)

In addition to the Git/scratch rules, allow only these explicit launcher
subcommands and nothing else on the launcher:

- `<launcher> analyze-git …`
- `<launcher> plan-git …`
- `<launcher> verify-git …`
- `<launcher> plugin workspaces` with **no further arguments** (no `--apply`,
  `--source-root`, runtime or grant option)

Must not match: the launcher binary as a whole, `grant-policy-run`,
`execute-policy-run`, `recover-policy-run`, or any other subcommand.

Also record as an input to SPEC-053 REQ-009 only: whether the host could
additionally express the single extra subcommand `analyze-claude-transcripts`
(gate v2 would need it; planning amendment approved 2026-10-24). This is a
what-can-the-host-express question only; do not run it.

### 4.3 Candidate rule shapes to try (unverified syntax)

Session flags (check `claude --help` on the chosen host for the current form):

```bash
claude --plugin-dir "<out>/plugins/agent-braid" \
  --allowedTools "mcp__plugin_agent-braid_agent-braid__workspaces" \
                 "mcp__plugin_agent-braid_agent-braid__analyze-work" \
                 "mcp__plugin_agent-braid_agent-braid__analyze" \
                 "mcp__plugin_agent-braid_agent-braid__prepare" \
  --disallowedTools "mcp__plugin_agent-braid_agent-braid__execute" \
                    "mcp__plugin_agent-braid_agent-braid__recover" \
                    "mcp__plugin_agent-braid_agent-braid__verify" \
                    "mcp__plugin_agent-braid_agent-braid__status"
```

Equivalent `--settings` JSON (`permissions.allow` / `permissions.deny`) for the
Bash rules, one entry per exact Git subcommand and the two scratch commands. Write
the file into the scratch area, not into a project, and record its full text in the
evidence. The names above are the ones visible in an unrelated installed-plugin
session at preparation time; verify them against HV-1 output and use what the host
really exposes.

## 5. HV-1 — plugin MCP tools inside workflow agents (T024)

**Setup:** §2 complete; analysis-only registration; candidate loaded. Run the
two-arm probe:

- **Arm A (analysis-only registration):** start a workflow whose single agent is
  asked only to list the plugin tool names visible to it and to call `workspaces`
  once and `analyze-work` once over `kind: git` commit sources
  `main` vs `agent/a` and `agent/b`. Alternatively run `/agent-braid:braid-gate`
  with the §3.2 arguments and read the MCP transcript. Record the exact tool names
  the agent sees and whether each call succeeds.
- **Arm B (runtime-enabled registration, deliberate and throwaway):** create a
  second registry home `$REG_RUNTIME`, register the same fixture with
  `--enable-runtime --grant-store "$SCRATCH/grants-empty"` (preview, inspect digest,
  apply once; the grant store directory stays empty), reconnect MCP, repeat the tool
  listing only. Do **not** call any runtime tool. Then remove that registration and
  the scratch grant store.
- **Deny probe (if the host supports it):** with `execute`, `recover`, `verify`,
  `status` in the deny list (§4.3), re-run Arm B and record whether the host hides
  or refuses them in the agent.

**Observation:** exact visible tool names per arm; whether `workspaces` and
`analyze-work` are callable from a workflow agent; whether the host can deny
`execute`/`recover`/`verify`/`status`.

**Pass:** `workspaces` and `analyze-work` visible and callable from a workflow agent
in Arm A, and in Arm B either the four runtime tools are absent or the host can
deny them. **Fail (recorded REQ-016 control failure):** `execute`, `recover`,
`verify` or `status` visible in a runtime-enabled registration and the host cannot
deny them. **Fail (fallback path):** MCP tools not visible to workflow agents at
all (then HV-5 decides whether the constrained-CLI fallback is possible).
**Unobserved:** the probe could not be started.

Evidence `evidence/hv-1.json` (+ `evidence/hv-1-transcript.txt`):

```json
{
  "task": "T024",
  "behavior": "HV-1 plugin MCP tools inside workflow agents",
  "claudeCodeVersion": null,
  "candidate": { "sourceCommit": null, "packageInventorySha256": null },
  "outcome": "pass | fail | unobserved",
  "armAnalysisOnly": {
    "registryHome": null,
    "visibleToolNames": [],
    "workspacesCallable": null,
    "analyzeWorkCallable": null,
    "rawResultExcerpt": null
  },
  "armRuntimeEnabled": {
    "registryHome": null,
    "visibleToolNames": [],
    "runtimeToolsVisible": { "execute": null, "recover": null, "verify": null, "status": null },
    "hostCanDeny": null,
    "denyRulesUsed": [],
    "runtimeToolCalled": false
  },
  "req016Control": "pass | fail | unobserved",
  "transcriptPath": null,
  "notes": null
}
```

(`runtimeToolCalled` must remain `false`; if you called one, record `true` and why.)

## 6. HV-2 — plugin agent definitions as `agentType` (T025)

**Setup:** §2; no gate needed (the gate ships no plugin agent; this only bounds
future design). Probe in the scratch workflow: spawn one agent with an
`agentType` that names a plugin-provided agent. The candidate has none, so use any
plugin agent definition the host lists for a trusted installed plugin, or the name
form `agent-braid:<name>` that would apply; if the host offers no way to enumerate
plugin agents, record `unobserved` with the reason.

**Observation:** accepted / rejected / error text, with the exact name form tried.
**Pass:** a plugin-defined agent resolves as `agentType`. **Fail:** host rejects the
plugin-namespaced agent type. **Unobserved:** no way to test with an available plugin
agent. R1 does not depend on this result.

Evidence `evidence/hv-2.json`:

```json
{
  "task": "T025",
  "behavior": "HV-2 plugin agent definitions as agentType",
  "claudeCodeVersion": null,
  "outcome": "pass | fail | unobserved",
  "nameFormsTried": [],
  "pluginUsedForProbe": null,
  "rawHostMessage": null,
  "transcriptPath": null,
  "notes": "gate ships no plugin agent; result bounds future design only"
}
```

## 7. HV-3 — nested call of the plugin workflow by name (T026)

**Setup:** §2, analysis-only registration, §3.1 and §3.2. Run both paths
**separately** and record each:

1. **Nested:** start `hv-ending`; observe whether `workflow('agent-braid:braid-gate', args)`
   (and any other name form tried) resolves and returns exactly one structured
   result (the gate envelope, `executionAuthorization: false`).
2. **Direct slash:** run `/agent-braid:braid-gate` as in §3.2.

A `refused` or `inconclusive` gate envelope still counts as **resolved** for this
item (the question is name resolution and the return of one structured result, not
the gate verdict); an unresolved name or no structured result does not.

**Pass (per path):** resolves and returns one structured result. **Fail:**
name not resolvable / no structured result. If the nested path fails and nesting is
the only integration path, there is no R1 gate (T029). **Unobserved:** the path
could not be tried.

Evidence `evidence/hv-3.json`:

```json
{
  "task": "T026",
  "behavior": "HV-3 nested call of plugin workflow by name",
  "claudeCodeVersion": null,
  "nested": {
    "outcome": "pass | fail | unobserved",
    "nameFormsTried": [],
    "resolvedName": null,
    "returnedOneStructuredResult": null,
    "gateStatus": null,
    "executionAuthorization": null,
    "rawHostMessage": null
  },
  "directSlash": {
    "outcome": "pass | fail | unobserved",
    "invocation": null,
    "argumentPassingThatWorked": null,
    "gateStatus": null,
    "rawHostMessage": null
  },
  "transcriptPath": null,
  "notes": null
}
```

## 8. HV-4 — resume after interruption (T027)

**Setup:** §2; use the gate itself on the fixture with 4 sources so it takes more
than a few seconds: `base: main`, `sources: [agent/a, agent/b, agent/c, agent/d]`.

1. Start the gate. Interrupt (stop) it after the **analyze** phase has finished and
   before it reports, using the host's native stop. Note which phase was running.
2. Relaunch using the host's native resume/relaunch for that run (record the
   exact gesture or command).
3. Observe which gate agents reran (validate / analyze / baseline / finalize), and
   count MCP calls in the transcript: any second concurrent MCP caller, any
   duplicate `analyze-work` or `prepare`, or a rerun of a completed agent.

**Observation:** per-agent rerun table, MCP call counts before and after resume,
final envelope status.
**Pass:** completed phases are not rerun or any rerun is harmless **and** no second
concurrent MCP caller and no duplicate `prepare` call occurred. **Fail:** a second
concurrent MCP caller or a duplicate `prepare` occurred. **Unobserved:** the host
offers no resume, or the run finished before it could be interrupted (state which).

Evidence `evidence/hv-4.json`:

```json
{
  "task": "T027",
  "behavior": "HV-4 resume after interruption",
  "claudeCodeVersion": null,
  "outcome": "pass | fail | unobserved",
  "sources": [],
  "interruptedDuringPhase": null,
  "resumeGesture": null,
  "agentsRerun": { "validate": null, "analyze": null, "baseline": null, "finalize": null },
  "mcpCalls": {
    "beforeInterrupt": { "workspaces": null, "analyze-work": null, "analyze": null, "prepare": null },
    "afterResume": { "workspaces": null, "analyze-work": null, "analyze": null, "prepare": null }
  },
  "secondConcurrentMcpCaller": null,
  "duplicatePrepareCall": null,
  "finalGateStatus": null,
  "transcriptPath": null,
  "notes": null
}
```

## 9. HV-5 — approval prompts, auto mode and the allowlist (T028)

**Setup:** §2 and §4. Run the gate (`main` vs `agent/a`,`agent/b`) once in each
mode. After each run, tear down nothing (same registry).

| Mode | How |
| --- | --- |
| manual | default interactive permission mode |
| accept-edits | `--permission-mode acceptEdits` (or the host's UI equivalent) |
| auto | the host's auto mode (record how enabled and whether available on the subscription; if it needs a paid tier, record `unobserved`, do not upgrade) |
| non-interactive | `claude -p "<prompt that starts the gate>"` with the §4.3 flags |

For each: record the prompt(s) shown (verbatim), whether the run needed per-run
approval, which Bash and MCP permissions the gate agents actually required, and
whether any prompt asked about a tool outside the §4 allowlist.

Allowlist expressibility (record per item, with the verbatim rule used and a
yes/no, plus the host's verbatim message when it rejected the rule):

1. Exact plugin tool allow for `workspaces`, `analyze-work`, `analyze`, `prepare`.
2. Deny / absence for `execute`, `recover`, `verify`, `status`.
3. Subcommand-level Git rules with the full hardened prefix (not a bare `git` rule).
4. The exact `mktemp -d "${TMPDIR:-/tmp}/braid-gate.XXXXXXXX"` rule.
5. The `rm -rf -- "<path>"` rule narrowed to a `braid-gate.XXXXXXXX` path under `TMPDIR`.
6. Constrained-CLI fallback list (§4.2): the three launcher subcommands and the
   exact no-argument `plugin workspaces` rule, and the absence of any rule matching
   the launcher as a whole (negative check: confirm `launch plugin setup …`,
   `grant-policy-run`, `execute-policy-run`, `recover-policy-run` prompt or are
   denied; **do not approve them**).
7. Input to SPEC-053 REQ-009 only: could the host also express
   `analyze-claude-transcripts` as one more explicit subcommand?
8. Per-agent separation (rules scoped per agent): available / not available.
   Subagents use the session's permission rules; record whether anything finer
   exists.

Also confirm and record: approving the run (or auto mode) was treated as **no**
Agent Braid authority; the gate returned `executionAuthorization: false`; no grant
or execute command was run.

**Pass (for R1):** the host can express items 1–5 narrowly (or item 6 if the MCP
path is unavailable) and no prompt outside the allowlist was required. **Fail:**
the host cannot express the narrow rules → baseline phase unavailable (item 4/5) or
fallback no-go (item 6); a host that cannot express item 6 (including per agent
when needed) is also recorded as a no-go input for SPEC-053 REQ-009. **Unobserved:**
mode not available on the subscription or run not possible; state which.

Evidence `evidence/hv-5.json`:

```json
{
  "task": "T028",
  "behavior": "HV-5 approval prompts, auto mode and permission allowlist",
  "claudeCodeVersion": null,
  "outcome": "pass | fail | unobserved",
  "modes": {
    "manual": { "observed": null, "promptsVerbatim": [], "perRunApprovalNeeded": null, "gateStatus": null },
    "acceptEdits": { "observed": null, "promptsVerbatim": [], "perRunApprovalNeeded": null, "gateStatus": null },
    "auto": { "observed": null, "availableOnSubscription": null, "promptsVerbatim": [], "gateStatus": null },
    "nonInteractive": { "observed": null, "command": null, "promptsVerbatim": [], "gateStatus": null }
  },
  "permissionsRequiredByGateAgents": { "bash": [], "mcp": [] },
  "promptOutsideAllowlistSeen": null,
  "allowlist": {
    "settingsFileText": null,
    "pluginToolAllow": { "expressible": null, "ruleUsed": null, "hostMessage": null },
    "runtimeToolDeny": { "expressible": null, "ruleUsed": null, "hostMessage": null },
    "gitSubcommandLevel": { "expressible": null, "ruleUsed": null, "hostMessage": null },
    "mktemp": { "expressible": null, "ruleUsed": null, "hostMessage": null },
    "rmRfScratch": { "expressible": null, "ruleUsed": null, "hostMessage": null },
    "fallbackLauncherList": {
      "analyzeGit": null, "planGit": null, "verifyGit": null,
      "pluginWorkspacesNoArgs": { "expressible": null, "ruleUsed": null },
      "launcherAsWholeMatchedByNoRule": null,
      "grantExecuteRecoverNotAllowed": null
    },
    "analyzeClaudeTranscriptsExpressible": null,
    "perAgentSeparation": "available | not available | unobserved"
  },
  "approvalTreatedAsAgentBraidAuthority": false,
  "executionAuthorization": false,
  "grantOrExecuteCommandRun": false,
  "transcriptPaths": [],
  "notes": null
}
```

(`approvalTreatedAsAgentBraidAuthority`, `executionAuthorization` and
`grantOrExecuteCommandRun` are the required values; if observation disagrees,
record the observed value and flag it.)

## 10. T029 — disposition record (after HV-1, HV-3, HV-5)

`evidence/hv-disposition.md` (free text, one line per behavior). Template:

```markdown
# SPEC-052 host-verification disposition
Claude Code version: <observed>
Candidate: sourceCommit <sha>, inventory sha256 <hash> (engineering-only)

| Id | Outcome (pass/fail/unobserved) | Version | Evidence file |
| --- | --- | --- | --- |
| HV-1 | | | evidence/hv-1.json |
| HV-2 | | | evidence/hv-2.json |
| HV-3 | | | evidence/hv-3.json |
| HV-4 | | | evidence/hv-4.json |
| HV-5 | | | evidence/hv-5.json |

Applied rule (from tasks.md T029): <which fallback / no-go clause applies, quoted>
- HV-1 failed? bundled-CLI fallback allowed only if HV-5 item 6 was expressible
- HV-3 failed and nesting the only path? no R1 gate
- Host cannot express the constrained Bash? recorded no-go input for SPEC-053 REQ-009
Decision basis only; no go/no-go on release (that is T037).
```

R1 depends only on HV-1, HV-3 (nested path) and HV-5.

## 11. After the probes

- T030–T032 follow only if T029 allows. T033/T037 are founder decisions.
- Clean up: remove the scratch registrations (`plugin workspaces --remove`,
  preview then apply), the scratch grant store and registry homes, uninstall or
  re-enable plugins changed in §2.2, and delete `$FIX` and `$SCRATCH` when done.
- Commit evidence files with the founder's own reviewed commit; this runbook's
  commit does not contain any evidence.
