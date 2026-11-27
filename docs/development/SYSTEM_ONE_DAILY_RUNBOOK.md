<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# System One daily runbook

One command, once a day, for the owner's S1.5b shadow-week counts: record the merge
outcomes of branches merged since the last run, join them to the shadow episodes, and
print the advised-pair counts, the false-independence count and its Wilson 95% upper
bound. It only reads what the owner already consented to
([SYSTEM_ONE_SHADOW.md](../tooling/SYSTEM_ONE_SHADOW.md)) and grants nothing:
`executionAuthorization` stays `false`.

Everything here is a thin wrapper over three commands that exist in the repository.
Run each with `--help` to see the flags. Python 3.12 or newer is required, the same
as the package.

| Step | Command | What it does |
|---|---|---|
| 1 | `python3 scripts/spec066_record_merge_outcomes.py --repository REPO --head REV --head REV ... --write` | Labels every pair of the given heads with `git merge-tree` and stores the outcomes. With `--write` and `systemOne` consent `shadow` or `advise`, it also stores one replay episode per new pair in a separate store (see below). Without `--write` it is a dry run (also the default). |
| 2 | `python3 scripts/spec066_s15b_observe.py --write` | Joins stored outcomes to the shadow episodes, appends joined records, writes the evidence JSON and applies the automatic rollback. `--yield-report` (the default) prints the same counts and writes nothing, and cannot roll back. |
| 3 | `agent-braid system-one report [--format json]` | Counts the retained shadow episodes per day and System 2 class. Optional context; the daily numbers below come from step 2. |

The recorder needs two or more heads (at most 12) and the observer needs no
arguments. The recorder has no "since last run" flag, so the one command below keeps
that state itself.

## The one command

Save once as a shell function (for example in `~/.zshrc`), then run `s1_daily` from
anywhere inside your agent-braid checkout. It needs `git`, `gh` (logged in), `jq` and
Python 3.12+. Set `S1_PYTHON` if your interpreter is not `python3.13`.

```bash
s1_daily() (
  set -uo pipefail
  repo=${S1_REPO:-$(git rev-parse --show-toplevel)} || exit 1
  py=${S1_PYTHON:-python3.13}
  state=${XDG_STATE_HOME:-$HOME/.local/state}/agent-braid-s1-daily
  mkdir -p "$state" && chmod 700 "$state"
  since=$(cat "$state/last-run" 2>/dev/null || date -u -v-1d +%Y-%m-%dT%H:%M:%SZ)
  write=--write; observe=--write
  [ -n "${S1_DRY:-}" ] && { write=--dry-run; observe=--yield-report; }

  # 1. Heads merged into develop since the last run, oldest first, at most 12 per run.
  rows=$(gh pr list --repo "$(git -C "$repo" remote get-url origin)" --state merged --base develop \
    --search "merged:>=${since%%T*}" --limit 100 --json headRefOid,mergedAt |
    jq -r --arg s "$since" '[.[] | select(.mergedAt > $s)] | sort_by(.mergedAt)[:12][]
      | "\(.headRefOid) \(.mergedAt)"') || { echo "s1_daily: gh failed" >&2; exit 1; }
  heads=(); stamp=$since
  while read -r oid merged; do
    [ -n "$oid" ] || continue
    git -C "$repo" fetch -q origin "$oid" 2>/dev/null   # a missing object is counted as objects-missing, not an error
    heads+=(--head "$oid"); stamp=$merged
  done <<<"$rows"

  echo "== merge outcomes since $since: $(( ${#heads[@]} / 2 )) head(s)"
  if [ "${#heads[@]}" -ge 4 ]; then
    (cd "$repo" && "$py" scripts/spec066_record_merge_outcomes.py --repository "$repo" "${heads[@]}" $write) |
      jq -c '{recorded: .pairs.recorded, enumerated: .pairs.enumerated, byKind: .pairs.byKind,
              skipped: .pairs.skipped, unlabelled: .pairs.unlabelled, store, episodes}' || exit 1
  else
    echo "fewer than 2 heads: recorder skipped (nothing lost; the next run starts from $since)"
    stamp=$since
  fi

  # 2. Observer: join, report, apply the automatic rollback (write mode only).
  out=$(cd "$repo" && "$py" scripts/spec066_s15b_observe.py $observe); rc=$?
  [ "$rc" -le 3 ] && [ -n "$out" ] || { echo "s1_daily: observer refused" >&2; exit 1; }

  # 3. The numbers.
  jq -r '"== System One daily counts \(.date) (\(.mode))
advised pairs in episodes : \(.falseIndependence.advisedPairsInEpisodes)  (rule-answered: \(.counts["rule-answered-pairs"]))
joined outcomes           : \(.falseIndependence.joinedOutcomes)  (on advised pairs: \(.falseIndependence.joinedOnAdvisedPairs), merge-clean: \(.falseIndependence.advisedMergeClean))
false independent         : \(.falseIndependence.falseIndependent)
false-independence rate   : \(.falseIndependence.falseIndependenceRate // "n/a (no textual verdict yet)")
Wilson 95% upper bound    : \(.falseIndependence.wilson95Upper // "n/a")
joined by kind            : \(.joinedByOutcomeKind | tojson)
auto-rollback recorded    : \(.autoRollbackRecorded // "n/a (yield-report cannot roll back)")"' <<<"$out"
  [ "$rc" -eq 3 ] && echo "WARNING: positive control failed (exit 3); do not trust these numbers" >&2

  # Advance the cursor only after both steps ran.
  [ -n "${S1_DRY:-}" ] || printf '%s\n' "$stamp" >"$state/last-run"
  exit "$rc"
)
```

`S1_DRY=1 s1_daily` is the safe preview: dry-run recorder, `--yield-report` observer,
no cursor update, no rollback. An unattended schedule can run `s1_daily` directly; the
outcome is the same as running it by hand.

If more than 12 branches merged since the last run, the run takes the 12 oldest and
moves the cursor to the last of them, so the next run continues. Pairs across two such
chunks are not labelled. Branches merged by someone else, or deleted objects that
cannot be fetched, are skipped by the recorder and counted (`author-excluded`,
`objects-missing`), not silently dropped.

## Replay episodes

Live shadow episodes are written only when `analyze-work` runs, so a quiet week
leaves nothing to join. To avoid that, step 1 with `--write` also stores, for each
pair it labels, the episode of the same pair of heads: the same analysis a live call
runs, salted with the registered source root, with the rule's answer and without the
verdict. These replay episodes live in their own store, `system-one-replay/` beside
`system-one/`, never in the live one. Rules, stated plainly:

- **Separate, descriptive only.** The observer joins an outcome to a live episode when
  it can and to a replay episode only when no live episode matches. Replay joins are
  counted as `joined-replay` and reported under `replayDescriptive`. The
  false-independence report, the Wilson bound, the D7 automatic rollback and the D8
  packet use live joins only.
- **True by construction.** The join of these pairs holds because both sides come from
  the same analysis. The episode is built after the merge and its day is the recorder
  run day. The rule reads only the two heads and never sees the verdict.
- **No doubling.** One replay episode is stored per pair resource lists, checked against
  the replay store's retained episodes, so a rerun on any day does not store a second
  one. The episode is stored before the outcome record, so a crash between the two
  leaves no outcome without its episode. A refused episode is counted as `refused:*`;
  rerunning the same heads stores it, because the check is by pair, not by record.
- **No backfill.** With `--day` other than today nothing is stored (`day-mismatch`), and
  an outcome record older than the retention window gets no episode. Without the
  registry's `shadow` or `advise` consent nothing is stored (`consent-off`).
  `episodes` in the recorder evidence counts `written`, `duplicate`, `no-episode-built`
  and `refused:*`.
- **Revocation.** `agent-braid system-one purge` removes both stores
  (`replayFilesRemoved`). Outcome records from before this step have no episode and
  stay `no-episode`.

## Reading the output

| Line | Meaning |
|---|---|
| advised pairs in episodes | pairs in retained shadow episodes where the DP-1 rule answered `likely-independent` (`counts["advised-pairs"]`); `rule-answered` counts every pair the rule answered, including `undetermined` |
| joined outcomes | outcome records matched to an episode pair and retained |
| on advised pairs | joined outcomes whose DP-1 rule answer was `likely-independent` |
| merge-clean | of those, textual verdict clean (a trial that passed) |
| false independent | of those, `merge-conflict`: advised `likely-independent`, but the merge conflicted |
| Wilson 95% upper bound | upper limit of the 95% Wilson interval for false independent over (merge-clean + false independent); `n/a` until the first textual verdict |

The bound is over advised pairs with a textual `git merge-tree` verdict. It is not a
calibrated accuracy, and a merge-clean pair is not proven semantically independent.
The unjoined counters mean: `no-episode` (no episode within the 7 days before the outcome), `pair-unmatched` (episodes exist in the window but none has the same left, right and shared resource pseudonym lists as the outcome; a salt outside the candidate set is not told apart from a list mismatch), `truncated` (a side has 32 or more resources).
A yield of zero joined outcomes is valid: pairs with a deleted or unsupported path,
more than 31 resources on a side, or no matching episode stay unjoined.

## When the status is `auto-rollback-false-independence`

This means the observer found a joined `merge-conflict` on a pair the DP-1 rule
called `likely-independent` while DP-1 was promoted, and appended a rollback record to
the promotion registry (`system-one-promotion.json`). DP-1 is now back to `shadow`.
You see it as `auto-rollback recorded : true` in the daily output (or
`"autoRollbackRecorded": true` in the evidence JSON), and as
`systemOne.promotion` reason `auto-rollback-false-independence` in `plugin-status`
after the MCP server reconnects. It acts only while the latest DP-1 record is an
owner go and the conflict is not older than that go, so repeated runs do not stack.

What to do, in order:

1. **Do nothing to the registry.** The rollback is already recorded and takes effect
   at the next MCP reconnect. Do not edit `system-one-promotion.json` or any evidence
   file; any edit invalidates the digest chain and promotes nothing.
2. **Stop treating the Wilson bound as a GO input.** The false-independence count is
   now at least 1. Record the day and the one-line reason in your decision notes; the
   evidence JSON `s15b-observe-<date>.json` already holds the counts.
3. **Keep running `s1_daily`.** Shadow counts continue; the rollback does not stop
   recording.
4. **Re-promotion is an owner decision, never automatic.** Review the conflict, then
   use `agent-braid system-one promote --decision-point DP-1 --go` (a preview), and
   `--confirm <previewDigest>` to record. A conflict older than the new go does not
   trigger another rollback.

## Privacy limits and where outputs go

- **Structural only.** Outcomes hold a closed outcome kind, the day and salted
  pseudonyms of the pair's resources; no path, branch name, commit hash, author or
  prompt. The owner e-mail is used to select commits and is not stored.
- **Admitted workspace only.** The recorder and observer refuse any repository the
  corpus consent does not admit; other workspaces' episodes are never joined,
  persisted or purged.
- **30-day retention.** Records are kept 30 days from their day and applied on read
  or write; identical bodies collapse. The shadow store keeps 30 UTC dates as well.

| Output | Location | Notes |
|---|---|---|
| Merge outcomes | `.claude/agent-braid-s1/merge-outcomes.jsonl` under the admitted workspace's source root | mode `0600`, gitignored; the recorder refuses to write if the path is not ignored |
| Joined outcomes | `~/.local/share/agent-braid/system-one-s15b/` | private, `0700`, beside the shadow store |
| Shadow episodes | `~/.local/share/agent-braid/system-one/` | see [SYSTEM_ONE_SHADOW.md](../tooling/SYSTEM_ONE_SHADOW.md) |
| Daily evidence JSON | `specs/066-system-one-shadow/evidence/s15b-observe-<date>.json` in the checkout | counts by closed key only; generated, never hand-edited; one file per day, rewritten by a same-day rerun |
| Cursor | `~/.local/state/agent-braid-s1-daily/last-run` | one timestamp, no other data |

The evidence JSON is written into the working tree. Leave the daily files uncommitted
and let the SPEC-066 owner track decide which to commit with its wave docs; do not
edit `specs/066-system-one-shadow/tasks.md` from this routine.

To revoke everything: `python3 scripts/spec066_s15b_observe.py --purge` removes the
S1.5b store and the merge-outcome file; `agent-braid system-one purge` removes the
shadow store. Both are needed.
