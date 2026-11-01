# SPEC-066 validation procedures

Each procedure records the command, candidate commit and artifact hashes,
environment, expected and actual outcome, negative controls and limits. The
automated procedures run as the named tests in `tests/test_system_one_shadow.py`;
their candidate-bound records are added when the candidate is frozen. The
owner-run real-use check stays separate from automated checks. Procedures 001–009
map to SC-001–SC-009.

| Procedure | Covers | Kind |
|---|---|---|
| procedure_001 | SC-001, REQ-002 | automated |
| procedure_002 | SC-002, REQ-003 | automated |
| procedure_003 | SC-003, REQ-002, REQ-004 | automated |
| procedure_004 | SC-004, REQ-005 | automated |
| procedure_005 | SC-005, REQ-001 | automated |
| procedure_006 | SC-006 | owner-run |
| procedure_007 | REQ-006 / SC-007 | automated |
| procedure_008 | REQ-007 / SC-008 | automated |
| procedure_009 | REQ-008 / SC-009 | automated |

## procedure_001

Build a service pair over the same owned roots, one with `system_one="off"` and one
with `"shadow"`, with `uuid.uuid4` and the clock fixed so the random run identifier
and any timestamp are equal. Call every tool the service exposes with the same
inputs, including at least: `analyze-work` with an AIM batch containing an
`unknown`, a `conflicting`, an `ordered` and an `independent-candidate` pair;
`analyze-work` with kind `git`; `analyze`; `prepare`; `status`; and, with runtime
enabled in a temporary fixture, `execute`, `recover` and `verify`. Assert the
serialized envelope bytes are identical between modes, and identical before and
after the shadow call for the same service (the observer did not mutate the
envelope, the arguments or the report). Negative controls: an observer that edits
the envelope fails; an observer that raises still returns the unchanged envelope;
a refused, cancelled or error envelope produces no episode.
Command: `python3 -m unittest tests.test_system_one_shadow_parity -v`.

## procedure_002

Validate episodes produced from owned fixtures against the contract with
`validate_episode`: one fixture per classification (including a report whose pair
carries both `dependency-order` and `read-version`), an AIM batch and a Git analysis
(`effectKinds` is `null` for both, because the report carries no effect kinds), a report with more than 64 pairs
(`pairsRecorded` 64, `pairCount` the total, first 64 in report order), and a report
with zero pairs. Assert the reason codes equal the table, the constraints are in the
closed set, the episode is canonical and single-line, and `observedOutcome` is
`null`. Privacy test: seed instance IDs, attempt IDs, resource names, paths,
repository names, prompts and a `ruleSet` string with distinctive sentinel values,
analyze, build the episode, serialize, and assert no sentinel appears anywhere in
the bytes. Drift test: scan the string literals appended to `reasons` in
`analysis._interaction` and assert each is in the table. Negative controls: an
unmapped sentence yields a `skipped` / `unmapped-reason` episode with no pairs; an
episode with one extra string field, one unknown reason code, one value outside the
effect-kind set, a negative count, `NaN`, a duplicate member, a missing field, or
`executionAuthorization` true is refused with a stable reason.
Command: `python3 -m unittest tests.test_system_one_shadow -v`.

## procedure_003

Store and containment. In a temporary home, append episodes and assert the day file
is mode `0600`, owned by the current user, with one hard link, in a directory of mode
`0700` outside any repository. Refusals, each leaving the caller's envelope unchanged
and the elapsed shadow time within the budget plus the fixed cost of one refusal:
a symlink at the file, at the directory and at each ancestor; a Git repository
ancestor; a group- or world-readable file or directory; a file with a second hard
link; a foreign-owned file where the platform allows it; a day file one byte under
and one byte over 4 MiB; a held lock (busy, refused at once with no wait); an
unknown file in the directory; a read-only directory; a full-disk error injected on
`write`. Each increments the in-memory counter for its reason and none raises.
Retention: with day files dated 31, 30, 29 and 0 days ago, an append keeps the
newest 30 UTC dates and removes the older. Budget: with an injected clock that
passes 50 ms before serialization, the episode is the minimal `skipped` /
`budget-exceeded` form. Concurrency: four threads appending at once yield only
whole, valid lines. Parity: the same hostile layouts are refused by the telemetry
path checker for the same reasons.
Command: `python3 -m unittest tests.test_system_one_shadow_store
tests.test_system_one_shadow_parity -v`.

Limit: the budget is checked between stages and cannot interrupt a blocking
filesystem call. A stalled disk is not simulated; the measured overhead (T021) is the
evidence for typical conditions.

## procedure_004

Seed a store with episodes of known composition across three UTC dates, both
operations, all four System 2 classes and all four System One statuses, including one
invalid line and one pair-capped episode. Run `system-one report` in text and in
`--format json`. Assert the JSON validates as `agent-braid-s1-report/v0.1`, the
counts per day, operation, class and status equal the seeds, the DP-1 opportunity
share equals the seeded `unknown` pairs over recorded pairs, `invalidLines` is 1, and
no output line contains an episode body or any field name of the pair object.
Report on an absent store prints zero counts and creates no file or directory.
`purge` without a terminal and without `--yes` refuses and deletes nothing; with
`--yes` it removes the episode files and the lock and leaves an unknown file in place
with a message. Negative controls: an unsafe store is refused by the report with the
same path rules; an episode that fails the validator is counted, never printed.
Command: `python3 -m unittest tests.test_system_one_shadow_store
tests.test_system_one_cli -v`.

## procedure_005

Digest and bytes. Create registries with `systemOne` absent and with `plugin setup
--system-one off` applied after `shadow`; assert the registry bytes and
`configuration_digest` equal those of a registry written by the current code, and
that the setup preview of a no-op reports `reconnectRequired` false. With
`shadow`, assert the member appears, the digest changes, a router started before the
change reports `reconnect-required`, and a router started after it builds services
with `ToolingConfig.system_one == "shadow"`. `ToolingConfig` refuses `"on"`, `""` and
`None`. Setup of `--system-one` alone is accepted; `--system-one` with an invalid
value is refused by argument parsing. A registry whose `systemOne` is not a string or
not `off`/`shadow` is refused as malformed. Telemetry consent does not change shadow
mode and vice versa. Negative control: a registry written with the member absent
from the key-set check fails the old strict decode, which is the documented
downgrade behaviour.
Command: `python3 -m unittest tests.test_system_one_shadow_consent
tests.test_plugin_registry -v`.

## procedure_006

Owner-run. On the owner machine, with the candidate package installed, run
`plugin setup --system-one shadow` (preview, then `--apply` with the printed digest),
reconnect the MCP, confirm `plugin-status` shows `activeMode: shadow`, and work
normally with at least one `analyze-work` call that has two or more
operations. Then run `agent-braid system-one report --format json`. Query every
source listed in `docs/development/REAL_USE_EVIDENCE.md`. Commit a derived receipt
with sources consulted, window, episode count, pair count, class and status counts,
DP-1 opportunity share, plugin and package version, and outcome; no identifiers, no
paths. A receipt with zero episodes is valid and is reported as "no observations",
with the reason if known. The receipt informs the S1.5b decision and grants nothing.
Evidence class: observational real use of one owner, not preregistered, not
randomized, not evidence of any System One utility.
Evidence: `evidence/real-use-shadow-<date>.json`.

## procedure_007

CLI telemetry. With `--telemetry local` and a temporary telemetry home, run
`system-one capabilities`, `decide` on a fixture, `report` and `purge --yes`; assert
the telemetry report shows `cli` / `system-one` cells with outcomes `ok` for exit
codes 0 and 1, `refused` for 2 and `error` otherwise, and no classification or
missing-summary cell for the new operation. With the default `--telemetry off` the
telemetry store is not created. Assert `OPERATIONS['cli']` equals the old tuple plus
`'system-one'`, that the batch schema and every other constant are unchanged, and
that the LIMITS text names the operation. Negative control: an imported batch that
carries `system-one` under the `mcp` surface is refused.
Command: `python3 -m unittest tests.test_tooling_telemetry tests.test_system_one_cli -v`.

## procedure_008

Identity. Assert the compiled backend ID and manifest digest equal
`system_one.BACKEND_ID` and the digest of `MODEL_MANIFEST`. Patch the installed digest
and assert the episode is `refused` / `identity-mismatch` with `answers: null` and
the envelope is unchanged. With the real identity, assert `abstained` /
`calibration-absent` with `answers: null` and a `manifestDigest` of 64 lowercase hex
characters. Negative control: a floating alias as backend ID is not accepted by the
validator. The test fails if the manifest changes without the constant.
Command: `python3 -m unittest tests.test_system_one_shadow -v`.

## procedure_009

Status. Call `plugin-status` in each state: absent registry, `off`, `shadow` configured
but not yet reconnected (configured `shadow`, active `off`), and active `shadow` with
no store, a present store and an unsafe store. Assert the `systemOne` block has
exactly `configuredMode`, `activeMode`, `store` and `episodeRetentionDays: 30`, the
store value is `absent`, `present` or `unsafe`, no call creates the directory or file,
and the output contains no episode content, path or counter. Negative control: a
status call against a store holding a hostile-text episode prints none of it.
Command: `python3 -m unittest tests.test_system_one_shadow_consent tests.test_plugin_mcp -v`.
