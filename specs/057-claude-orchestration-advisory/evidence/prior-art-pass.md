# SPEC-057 prior-art delta pass (T002), 2026-10-25

This is a delta record. It cites the recorded pass in `research/radar/2026-10-24-claude-orchestration.json` (SHA-256 `c034a6108a242a9dcb3181cad698fc0e6f364cf0eb59779d4c232a71d060ffaa`, entries RAD-2026-016 to RAD-2026-033, with the ECOSYSTEM.md section and adoption track AT-2026-007) and does not copy its content. It is a draft record: human review is pending, no approval is inferred, and it records no product, speed or value claim.

Method: read-only calls only (`gh api` GET against the GitHub REST API, one HTTP GET of the Codeberg page, `export.arxiv.org` query API). Nothing was installed, cloned or executed, no tool behavior was reproduced, and the spend was EUR 0. Date of the pass: 2026-10-25 (UTC). Repository head when run: `8d24c6f`.

Repeat rule (`tasks.md` T002): this pass must be repeated before SPEC-058 release and at M4.6 closure, in addition to before any publication wording. Everything below expires at the next pass.

## Queries

Status values: `repeated` (a query from the recorded set, re-run unchanged), `new` (extends the recorded set at a gap the record lists). Result counts are `total_count` from the search endpoint at the time of the call and are not stable.

| Id | Query | Type | Status | Date | Result |
|---|---|---|---|---|---|
| Q01 | `gh api search/repositories`: claude code multi-agent coordination | repository search | repeated | 2026-10-25 | 211 results; top five already known or generic prompt collections |
| Q02 | claude code worktree conflict agents | repository search | repeated | 2026-10-25 | 16 results; includes OpenWeft and Radar (recorded) and four names not in the radar (see Surfaced, not read) |
| Q03 | claude code file lock hook agents | repository search | repeated | 2026-10-25 | 3 results; two names not in the radar |
| Q04 | topic:claude-code multi-agent coordination | repository search | repeated | 2026-10-25 | 212 results; Cotal appears (359 stars) |
| Q05 | git worktree conflict detection ai coding agents | repository search | repeated | 2026-10-25 | 2 results: DriftWatch, Orchestune (both recorded) |
| Q06 | merge queue ai agents bisecting | repository search | repeated | 2026-10-25 | 1 result: SVRF (recorded) |
| Q07 | semantic merge tool tree-sitter git merge driver | repository search | repeated | 2026-10-25 | 0 results |
| Q08 | topic:claude-code-plugin conflict | repository search | repeated | 2026-10-25 | 17 results; none about multi-agent file ownership on the names and descriptions shown |
| Q09 | agent teams claude code conflict | repository search | repeated | 2026-10-25 | 6 results; relayBrain and TeamBus (recorded) |
| Q10 | topic:merge-queue | repository search | repeated | 2026-10-25 | 77 results; claude-code-merge-queue (recorded), uber/submitqueue and bimsonz/keel not in the radar |
| Q11 | mergiraf | repository search | repeated | 2026-10-25 | 15 results; mirrors and packaging of the recorded tool |
| Q12 | claude-code-plugin orchestration parallel agents conflict | repository search | repeated | 2026-10-25 | 0 results |
| Q13 | agent teams claude code hooks file ownership | repository search | repeated | 2026-10-25 | 0 results |
| Q14 | claude code parallel agents ownership hook PreToolUse deny worktree | repository search | repeated | 2026-10-25 | 0 results |
| Q15 | semantic merge driver git syntax-aware | repository search | repeated | 2026-10-25 | 0 results |
| Q16 | marketplace keyword filter over `anthropics/claude-plugins-official` `.claude-plugin/marketplace.json` (blob sha `4013c22afd516f1108134c87ed2d6f9839526e85`), keywords worktree, parallel, multi-agent, orchestrat, coordinat, conflict, merge, swarm, agent team, lock, on name and description | marketplace sweep | repeated | 2026-10-25 | 315 plugins; ten keyword hits, none describing multi-agent file ownership, worktree conflict detection or effect-hazard analysis (the hits are unrelated integrations, a data-platform agent, and the Mergify merge-queue CLI skills) |
| Q17 | direct reads by name of the recorded repositories | existence check | repeated | 2026-10-25 | see Repository re-verification |
| N01 | claude code multi-agent coordination created:>=2026-10-24 | repository search | new (entrants after 2026-10-24) | 2026-10-25 | 1 result: JF3Env/opencode-coordination |
| N02 | claude code worktree conflict agents created:>=2026-10-24 | repository search | new (entrants) | 2026-10-25 | 0 results |
| N03 | claude code agents file ownership hook created:>=2026-10-24 | repository search | new (entrants) | 2026-10-25 | 0 results |
| N04 | parallel coding agents conflict detection created:>=2026-10-24 | repository search | new (entrants) | 2026-10-25 | 0 results |
| N05 | coding agents merge queue created:>=2026-10-24 | repository search | new (entrants) | 2026-10-25 | 0 results |
| N06 | read-set validation coding agents | repository search | new (read-side check) | 2026-10-25 | 0 results |
| N07 | declared read write effects agents worktree | repository search | new (read-side check) | 2026-10-25 | 0 results |
| N08 | arXiv query API by identifier for the three recorded preprints and the five newly identified ones | peer-reviewed-literature gap (preprints in scope) | new | 2026-10-25 | see Literature |
| N09 | arXiv query API, title and abstract terms for STORM, Atomix, MPAC, Claim Plane, "freshness guard", self-report over-claim | literature gap | new | 2026-10-25 | STORM not identified; the others identified |

The gap list in the radar names four gaps. This pass touched them as follows.

| Gap named in the radar | Handled | How |
|---|---|---|
| A peer-reviewed literature query | partly | N08 and N09 reach arXiv preprints. No peer-reviewed venue index was queried, so no peer-reviewed claim is made |
| Commercial products | not handled | Conductor, Nimbalyst, Sculptor, Devin, Jules, Amp, Cursor and Copilot agent were not re-read; the radar limits still apply |
| Plugin directories other than the official marketplace snapshot | not handled | the official snapshot alone was re-swept (Q16); GitHub topic search (Q08) is not a directory |
| Entrants after 2026-10-24 | partly | N01 to N05 are a single-day window with name, description and topic matching |

## Sources read and not read

Read in this pass (by the method above, to the depth stated):

- GitHub repository metadata (existence, archived flag, stars, last push, license identifier) for 22 repositories; no README was read in this pass.
- The Codeberg page for Mergiraf, status code only.
- GitHub search result lists for Q01 to Q15 and N01 to N07 (names, creation and push dates, counts).
- Repository descriptions (one line each) for the ten names in Surfaced, not read.
- The marketplace manifest of the official plugin marketplace, filtered as in Q16.
- arXiv abstracts for the eight identifiers in Literature (abstract text and listed version only).

Not read in this pass:

- Any README beyond the descriptions above; the README reads of the radar (2026-10-24) are not repeated, so the radar classification is carried forward unchanged and not re-derived.
- Full text of any paper; all eight rows below are abstract-level.
- Commercial products and plugin directories other than the official snapshot (see the gap table).
- Native Claude Code feature documentation, which this pass did not re-fetch.
- Any peer-reviewed venue index.

## Repository re-verification

All 22 GitHub repositories exist, are public and answered a read-only metadata call on 2026-10-25; Mergiraf's Codeberg page answered with status 200. `andrehrferreira/claude-net` is archived, as recorded. git-kura and Radar, which the task names, both exist: `tooppoo/git-kura` (0 stars, last push 2026-09-14, Apache-2.0, unchanged since the radar) and `Jake-Network/radar` (2 stars, last push 2026-10-17, MIT, unchanged). Stars and pushes are point-in-time.

| Repository | Exists | Archived | Stars | Last push (UTC date) | License id | Radar entry |
|---|---|---|---|---|---|---|
| gastownhall/gastown | yes | no | 18533 | 2026-10-25 | MIT | RAD-2026-016 |
| gastownhall/beads | yes | no | 28205 | 2026-10-25 | MIT | RAD-2026-017 |
| Dicklesworthstone/mcp_agent_mail | yes | no | 2225 | 2026-10-23 | NOASSERTION | RAD-2026-018 |
| clash-sh/clash | yes | no | 65 | 2026-07-17 | MIT | classification basis |
| ThatHunky/agent-coord | yes | no | 1 | 2026-06-26 | MIT | RAD-2026-019 |
| ilyasibrahim/claude-agents-coordination | yes | no | 87 | 2026-05-30 | Unlicense | RAD-2026-021 |
| tooppoo/git-kura | yes | no | 0 | 2026-09-14 | Apache-2.0 | RAD-2026-020 |
| andrehrferreira/claude-net | yes | yes | 0 | 2026-03-13 | MIT | classification basis |
| smtg-ai/claude-squad | yes | no | 8667 | 2026-08-20 | AGPL-3.0 | classification basis |
| kbwo/ccmanager | yes | no | 1273 | 2026-10-25 | MIT | classification basis |
| Jake-Network/radar | yes | no | 2 | 2026-10-17 | MIT | RAD-2026-022 |
| Vignesh-P-C/DriftWatch | yes | no | 2 | 2026-09-15 | none reported | RAD-2026-023 |
| NeuraCerebra-AI/openweft | yes | no | 2 | 2026-09-09 | MIT | RAD-2026-024 |
| Saltmu/orchestune | yes | no | 1 | 2026-10-25 | MIT | RAD-2026-025 |
| nybarius/SVRF | yes | no | 2 | 2026-10-25 | NOASSERTION | RAD-2026-026 |
| funador/claude-code-merge-queue | yes | no | 131 | 2026-08-24 | MIT | RAD-2026-027 |
| Beastburner/teambus | yes | no | 0 | 2026-10-24 | MIT | RAD-2026-028 |
| prakrititz/relayBrain | yes | no | 32 | 2026-10-18 | MIT | RAD-2026-029 |
| QIU-Guanzong/CoProgrammer | yes | no | 1 | 2026-10-23 | MIT | RAD-2026-030 |
| fagemx/edda | yes | no | 36 | 2026-09-26 | Apache-2.0 | RAD-2026-031 |
| Arrmlet/tracecraft | yes | no | 31 | 2026-08-16 | MIT | RAD-2026-031 |
| anthropics/claude-plugins-official | yes | no | 44518 | 2026-10-25 | Apache-2.0 | RAD-2026-033 |
| mergiraf/mergiraf (Codeberg) | page answers | not checked | not checked | not checked | not checked | RAD-2026-032 |

Observed changes since the radar that matter: SVRF, Orchestune, Gas Town and Beads show a push dated 2026-10-25, after the push dates the radar recorded, so their READMEs may have changed since they were read; the radar classification is not re-derived here. TeamBus now shows 0 stars where the radar recorded none. Nothing was found that contradicts a radar classification, but just metadata was re-read, so this is not a confirmation of the READMEs either.

## Surfaced, not read

These names appeared in the repeated or new queries and are not in the radar. A one-line repository description was read; the README and behavior were not. They are not classified, and the bounded claim below does not cover them. The next pass reads their READMEs.

| Repository | Stars | Last push | One-line description as listed (summarized) | Relevance to classification |
|---|---|---|---|---|
| phalladar/tracon | 3 | 2026-10-17 | monitor for parallel Claude Code subagents: stuck agents and worktree file conflicts | possible textual-conflict or liveness comparator |
| katyella/legio | 5 | 2026-03-11 | fleet of worktree workers with SQLite mail and tiered merge | launching, messaging, merging |
| PenguinMiaou/claude-hive | 1 | 2026-03-31 | cross-window coordination with automated conflict detection | possible textual-conflict comparator |
| sezeryavuz/parallel-sessions | 5 | 2026-07-19 | file locking, crash recovery and task delegation across sessions | locks and recovery |
| dipakkr/agentsync | 0 | 2026-08-08 | shared plan with file-scope claims | path claims |
| Cotal-AI/Cotal | 359 | 2026-10-25 | described as an open standard for agent coordination; named in the radar classification basis for messaging but has no radar entry | messaging, possible protocol overlap |
| bimsonz/keel | 53 | 2026-10-23 | Git platform for software agents | unclear |
| uber/submitqueue | 241 | 2026-10-24 | speculative merge queue | integration stage, general-purpose |
| JF3Env/opencode-coordination | 0 | 2026-10-25 | roles, work items and messages on an append-only ledger (new entrant) | ledger and messaging |
| jrbrugger/morpius-plugin | 0 | 2026-08-10 | design-ontology grounding with conformance hooks | probably not relevant |

## Literature

Read depth for every row: abstract text from the arXiv query API, plus the listed version. No full text was read. The numbers in the "Quantitative literature claims" table of `research.md` carry the same rows.

| Short name | Identifier and listed version | Date read | What exactly was read | Relation to the specification |
|---|---|---|---|---|
| S-Bus | arXiv:2605.17076, v2 listed (v1 read on 2026-10-24) | 2026-10-25 | abstract of v2 | read-set reconstruction for shared HTTP state; the abstract states a v2 update, so the radar record of v1 is stale in version |
| CooperBench | arXiv:2601.13295, v2 listed (v1 read on 2026-10-24) | 2026-10-25 | abstract of v2 | benchmark of two-agent coding cooperation; cited as a benchmark, no figure used |
| MERGEGYM | arXiv:2610.04779, v1 | 2026-10-25 | abstract of v1 | the 47.3 percent figure (79 of 167 conflicts, stratified 715-pair set) is confirmed in the abstract; still a share within a stratified sample, not a prevalence |
| Atomix | arXiv:2602.14849, v2 | 2026-10-25 | abstract of v2 | progress-aware transactions recording reads and effects at runtime; prior art for the technique |
| MPAC | arXiv:2604.09744, v1 | 2026-10-25 | abstract of v1 | multi-principal coordination protocol with intent declaration and optimistic concurrency; prior art for the technique; its reported benchmark figure was not read in full and is not used |
| Claim Plane (design) | arXiv:2607.21909, v1 | 2026-10-25 | abstract of v1 | pre-write admission over declared change intents; prior art for ownership claims |
| Claim Plane (study) | arXiv:2608.00947, v1 | 2026-10-25 | abstract of v1 | 30-pair study; the abstract reports 46 of 90 dynamic executions failed closed on undeclared scope, which matches the use in research.md as a warning about fail-closed costs, not as a rate |
| Stale Does Not Mean Unsafe | arXiv:2609.29522, v1 | 2026-10-25 | abstract of v1 | source of the 92 to 95 percent figure, see below |
| STORM | not identified | 2026-10-25 | nothing; four arXiv queries returned no matching paper | cited by name in `spec.md` and `research.md` with no identifier; unresolved |

The two figures removed from the specification:

- 92 to 95 percent: found in arXiv:2609.29522v1. The abstract says freshness-based guards needlessly block 92 to 95 percent of benign races in a deterministic simulator with small locally hosted models. This is the share of benign races that a guard blocks, not the share of blocked races that are benign, which is how the digest paraphrased it. Verified against the abstract, with the corrected meaning; it concerns infrastructure state races, not Git worktrees. It stays out of the specification; the qualitative statement in `research.md` (a read/write overlap verdict can be a false positive) does not depend on the number.
- 32 to 49 percent: found in the v2 abstract of arXiv:2605.17076, which says agent self-reports over-claim shard usage by 32 percent (LLM judge) to 49 percent (human annotator), single author, in that paper's shard workload. The sentence is attributed to a v2 update, so it was not in the version read on 2026-10-24. Verified against the abstract of v2; it is not a measure of over-claiming of shared resources in coding agents, and it stays out of the specification.

Unresolved: STORM. The radar says it must not be cited by name or number until identified, yet `spec.md` and `research.md` still name it. This pass does not edit those lines; the owner of the specification text must identify STORM or drop the name. T002 is therefore not complete.

## Consistency with the radar classification

Parity, behind and easily copied items are carried forward unchanged from the radar. Nothing in this pass moves a capability between classes: no README was re-read, and the ten unread names above are not used as parity or behind evidence. The git-kura row stays marked as a README read and unused as parity or behind evidence. "Reporting unknown or missing evidence" stays parity and is not claimed as a standalone differentiator. Absence in a search result list is recorded as absence from that list, not as absence of a tool.

## Bounded claim

The permitted claim stays the single bounded sentence of `docs/strategy/ECOSYSTEM.md`, with its query set and date of 2026-10-24. This pass repeats the same query set on 2026-10-25 and finds no new match for read-set validation with explicit coverage (N06, N07, Q12 to Q14 return 0), but it also surfaces ten unread names, so it does not support a narrower or a broader statement. The fallback form, if the sentence is shortened, is: `no surveyed shipped plugin found` (query set Q01 to Q16 and N01 to N07, 2026-10-25, with the ten unread names excluded from the surveyed set).

## Limits

- GitHub search matches names, descriptions and topics and ranks by stars; low-visibility repositories can be missed, and counts vary between calls.
- Only metadata and abstracts were read; nothing was reproduced.
- Star counts, pushes and versions are point-in-time observations on 2026-10-25.
- The field moves daily; this record is stale after the next push to any listed repository.
- arXiv preprints are not peer-reviewed publications; no peer-reviewed claim is made.

## Machine-readable summary

```json
{
  "recordVersion": "0.1.0",
  "task": "T002",
  "date": "2026-10-25",
  "radar": {
    "path": "research/radar/2026-10-24-claude-orchestration.json",
    "sha256": "c034a6108a242a9dcb3181cad698fc0e6f364cf0eb59779d4c232a71d060ffaa"
  },
  "queryIds": ["Q01", "Q02", "Q03", "Q04", "Q05", "Q06", "Q07", "Q08", "Q09", "Q10", "Q11", "Q12", "Q13", "Q14", "Q15", "Q16", "Q17", "N01", "N02", "N03", "N04", "N05", "N06", "N07", "N08", "N09"],
  "repositoriesChecked": 22,
  "repositoriesMissing": 0,
  "unreadNames": 10,
  "preprintsRead": 8,
  "preprintsUnidentified": ["STORM"],
  "boundedClaimSource": "docs/strategy/ECOSYSTEM.md",
  "t002Complete": false,
  "repeatBefore": ["SPEC-058 release", "M4.6 closure", "any publication wording"]
}
```
