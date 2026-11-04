<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# SPEC-068 T010: owner runbook for the interactive rows

Companion of [`evidence/native-observation.json`](evidence/native-observation.json).
A track already recorded everything that needs no model turn (rows 01 to 15:
14 `observed`, 1 `contradicts`, row 14). This runbook is for rows 16 to 20, which need a
model session. Nothing here publishes, tags or releases anything, and nothing here is
a grant. Rows 21 to 23 (`github:` transport, Linux, `_meta`) stay `unobserved`.

Replace `<worktree>` with the absolute path of the track worktree,
`~/Repos/Personal/agent-braid-068-t010` (it is also where the candidate lives).

## What is already prepared (all untracked, in `<worktree>/.t010`)

| Item | Where |
|---|---|
| Candidate build (macOS arm64, version string `0.1.0-alpha.6`, source commit `841c2508`) | `.t010/candidate` |
| Local Git source for it (branch `candidate`, tag `t010-candidate`) | `.t010/source.git` |
| Source string to use, exactly | `.t010/source-string.txt` |
| Disposable OpenCode profile with the candidate already installed and one throwaway workspace registered | `.t010/profile` |
| Throwaway registered workspace (a one-file Git repository) | `.t010/ws-throwaway`, workspace id `6cb1f07e39191fa91feafa9ff4a81a02` |
| Environment file that puts a shell into the profile | `.t010/env.sh` |

The source string is
`git+file://<worktree>/.t010/source.git#candidate::path:plugins/agent-braid`
(with `<worktree>` expanded; the file holds the expanded form). The candidate carries
the version string of published alpha.6, so identify it by the inventory digest in the
JSON (`4e010137...`), not by the version.

## 0. Open the profile (dedicated terminal tab)

First keep the untracked `.t010/` out of Git, because option A below stores a provider
login inside it: `echo '/.t010/' >> "$(git -C <worktree> rev-parse --git-path info/exclude)"`
(local, not tracked). Later stage only the two named files, never `git add -A` or `.`.

`env.sh` redirects `HOME` and the four `XDG_*` variables into the profile, so use a tab
you close afterwards (`~` points into the profile there).

```sh
cd <worktree>/.t010 && . ./env.sh
$OC debug paths | head -5          # all five paths must be under .t010/profile (the tmp line below them is the shared system temp)
$OC service set port 47618         # a fixed unique port; the default 49374 may belong to your real OpenCode
$OC plugin list                    # may say "No plugins found" when cold; repeat after ~5 s:
                                   # expect "agent-braid  b092f0d  git+file://...#candidate::path:plugins/agent-braid"
```

If `debug paths` shows anything outside `.t010/profile`, stop and do not continue.
Note that OpenCode still reads your real `~/.agents/skills` and `~/.claude/skills`
(row 06); that is read-only and expected.

## 1. Model provider: two options

| Option | How | Trade-off |
|---|---|---|
| A (recommended): log in inside the disposable profile | `$OC auth login`, then pick the provider; credentials are stored under `.t010/profile/data/opencode` | Nothing touches your real profile or your real Agent Braid registry; you sign in once more (a browser may open for OAuth); delete the profile afterwards to drop the stored login. If your provider reads an API key from an environment variable, exporting it in this one tab is an equivalent, lighter variant. |
| B: use your real profile | Not provided. It would install the candidate globally into your real `~/.config/opencode` and use your real Agent Braid registry, and the record could not call itself a clean profile (REQ-012). Avoid it. If you insist, set `AGENT_BRAID_HOME` to a private directory and run step 11's `plugin remove` afterwards. | Faster login, but real configuration changes and a contaminated observation. |

Do not use `auth export` to copy credentials between profiles: it prints secrets.
Never paste credentials, the server password or tokens into the JSON or the PR.

## 2. Start OpenCode in the throwaway workspace

```sh
$OC "$T010/ws-throwaway"
```

(The managed service on port 47618 is expected to start on demand; not recorded with a TUI. If the TUI cannot reach the
plugin, `$OC plugin list` in a second tab shows whether it is loaded.)

Use only the throwaway workspace. Do not register your real repositories in this
profile. Do not ask the model to execute anything and never create a grant.

## 3. Skills and tool names (row 19, first part of row 16)

Type to the model, exactly:

> List the skills you can load whose names are analyze, plan, evidence, execute,
> recover or setup, and list the exact names of every tool whose name starts with
> `agent-braid`. Do not call any tool.

Expected from the automated part: the six skills; five tools after the reload done at
setup (`analyze-work`, `analyze`, `prepare`, `plugin-status`, `workspaces`), probably
shown as `agent-braid_<tool>` (codemode false, legacy protocol). Record what you
actually see, including whether the names are prefixed or wrapped.

## 4. Tool call and approval prompt (row 20)

> Call the `plugin-status` tool of the agent-braid server and show me `status`,
> `pluginVersion`, `registryHome` and the workspace ids.

Record: whether OpenCode asked for approval (and what the prompt text and choices
were) or ran it directly; the tool id shown; the result. Expected result:
`status configured`, `pluginVersion 0.1.0-alpha.6`, a `registryHome` inside the
profile, one workspace id `6cb1f07e39191fa91feafa9ff4a81a02`. If you are asked to
allow, allow once (not "always") so the next call shows the prompt again.

## 5. Analyze skill on the registered workspace (row 16, row 20)

> Use the analyze skill. Workspace id 6cb1f07e39191fa91feafa9ff4a81a02. Two proposed
> units of work: unit one edits README.md, unit two edits README.md. Report the
> result and its limits. Do not execute or prepare anything.

Record: whether the model loaded the skill (and whether it used the `analyze` skill
or a different one), that `agent-braid_analyze-work` was called with the explicit
workspace id, an approval prompt if any, the verdict, and that the limits mention no
execution authority. Expected (not yet observed): a valid core result with the same-file pair not
classed independent. The only recorded `analyze-work` run used disjoint files. If the
model cannot build valid input, record that as the result.

## 6. `agent-braid-setup` (row 17)

Type `/agent-braid-setup` (or choose it from the command list). Record whether it is
offered, what the session receives (the packaged `setup` skill text), and what the
model does. Decline any registry change it proposes: the profile is already set up.
This is also the first observation of the `execute` and `session.prompt` shapes.

## 7. Approval behaviour summary (row 20)

Write down for each tool call so far: prompted or not, the wording, and whether
"allow always" was offered. Do not change any permission setting.

## 8. `agent-braid-reconnect` and `opencode reload` (rows 17, 18)

In the open session type `/agent-braid-reconnect`. Record the message it sends (it
should name `opencode reload` or a restart and perform no reload itself). Then, in a
second tab with `. ./env.sh` sourced:

```sh
$OC service status          # note the URL, expected http://127.0.0.1:47618
$OC reload                  # every recorded reload used --server or ran in profile2; against the managed service this is unverified
```

Back in the SAME session, ask again for the `plugin-status` result and note whether
the call still works. Then start a NEW session in the TUI and ask once more. Both
should work after a reload with an unchanged version.

## 9. Optional: tools after a registry change in a live session (row 18)

Skip if short on time. In a second tab: register a second throwaway directory with the
candidate's launcher against the profile registry, then compare what the open session
and a new session list:

```sh
INST=$(cat "$T010/installed-path.txt")
mkdir -p "$T010/ws-two" && ( cd "$T010/ws-two" && git init -q . && echo x > a && git add a \
  && git -c user.name=t -c user.email=t@invalid.example commit -qm i )
"$INST/launch" plugin setup --home "$HOME/Library/Application Support/AgentBraid" \
  --source-root "$T010/ws-throwaway" --source-root "$T010/ws-two"      # preview: copy the previewDigest
"$INST/launch" plugin setup --home "$HOME/Library/Application Support/AgentBraid" \
  --source-root "$T010/ws-throwaway" --source-root "$T010/ws-two" --apply --preview-digest <digest>
```

Ask the open session for `plugin-status` (expect `reconnectRequired true` until
`$OC reload`), then reload and repeat. This is the REQ-005 behaviour in a live session.

## 10. New plugin version needs a new session (row 18)

Claude Code did not switch an open session to a newly installed plugin version. To see
what OpenCode does, publish a trivial new commit to the local source and update:

```sh
git clone -q "$T010/source.git" "$T010/upd-work" && cd "$T010/upd-work"
echo probe > T010-UPDATE-PROBE.txt && git add T010-UPDATE-PROBE.txt
git -c user.name=t -c user.email=t@invalid.example commit -qm "update probe" && git push -q origin candidate
cd "$T010" && rm -rf "$T010/upd-work"
$OC plugin check            # expect "(update available)"
$OC plugin update           # expect "Updated Server plugin"; a second cache epoch directory appears
$OC reload
```

(This pushes to the shared `source.git` (row 11 used a copy), so the profile no longer
sits at 'no update available'; it moves the local branch to a new commit; plugin bytes stay the same, so the
inventory digest in the record still identifies the candidate. Note the new short
commit.) In the OLD open session ask for `plugin-status` and note the path in
`bundledCli` (it contains the cache epoch directory: `.../npm/git-source-.../<epoch>/...`).
Then open a NEW session and repeat. Record whether the old session keeps the old epoch
directory and the new session uses the new one, or both switch.

## 11. Removal (also completes SC-006 at the real host)

```sh
$OC plugin remove "$(cat $T010/source-string.txt)"   # exact string; the package name only says "not configured"
cat "$XDG_CONFIG_HOME/opencode/opencode.json"          # expect {"plugins": []}
$OC reload; sleep 6; $OC plugin list                   # expect "No plugins found"
ls "$HOME/Library/Application Support/AgentBraid"      # expected: Agent Braid's own registry stays (not shown by the automated part)
find "$XDG_CACHE_HOME/opencode/npm" -maxdepth 3        # the installed cache directories stay
```

In the TUI (new session) check that the six skills, the two commands and the tools
are gone. Record any leftover. This is the last step: the profile no longer has the
plugin afterwards. To observe again, add it back with
`$OC plugin add "$(cat $T010/source-string.txt)"`.

## 12. Stop everything you started

Quit the TUI first, then:

```sh
$OC service stop
pgrep -f "$T010/profile" | wc -l      # expect 0 (also matches profile2); otherwise list with pgrep -fl and stop those
```

Close the tab. Delete the profile before any `git add` and only when you are done:
`rm -rf <worktree>/.t010/profile <worktree>/.t010/profile2` (this also deletes any
stored provider login of option A).

## Filling the JSON

Edit `specs/068-opencode-native-integration/evidence/native-observation.json`:

| Row | Question | Filled by |
|---|---|---|
| `16-skill-invocation-in-session` | skill listed to the model and invoked | steps 3, 5 |
| `17-command-execution` | `agent-braid-setup` and `agent-braid-reconnect` effects | steps 6, 8 |
| `18-new-session-after-new-version` | live session versus new session, after reload and after update | steps 8, 9, 10 |
| `19-model-facing-tool-names` | names the model sees | step 3 |
| `20-host-tool-call-and-approval` | `plugin-status`, `analyze-work`, approval prompts | steps 4, 5, 7 |

For each row you completed: set `status` to `observed` and fill `method`, `commands`
(what you typed), `observation` (short quotes of what you saw, one statement per item;
never secrets) and `limits`. Use `contradicts` instead of `observed` when the result
differs from the expectation written in the step or from
`contracts/opencode-surface.md`, and say how. Leave a row `unobserved` if you did not
do it, and keep its `limits`. Do not infer an observation; if the TUI showed nothing,
write that.

Then update `observedBy` (for example "track (automated, no model turn); owner
(interactive rows)"), `date` of your part, the top-level `status`, and the counts in
`summary`; if step 11 shows something different from row 11 (the automated update and remove
observation), add a short note to that row's `observation`. Validate and commit on the branch of the
draft PR (stage only `specs/068-opencode-native-integration/evidence/native-observation.json`):

```sh
.venv-speckit/bin/python -m scripts.validate_spec_kit
```

Marking the PR ready, ticking T010 in `tasks.md` and any release decision are yours;
the track did not do them. If a result changes a decision, record it in the JSON and
say so in the PR instead of editing the contract here.

## Findings to know before you start

- Row 14 (`contradicts`): the host loads skills from directories above the project's
  Git root, and such a skill replaced the plugin's skill, but `plugin doctor --host
  opencode --project` reported nothing. The contract limits the scan to the range from
  the directory to the Git root. A coordinator decision is open.
- Row 06: HOME redirection does not stop OpenCode from reading your real skill
  directories.
- Row 01: the candidate's version string is `0.1.0-alpha.6`.
