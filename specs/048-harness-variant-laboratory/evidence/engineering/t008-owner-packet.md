# SPEC-048 T008 owner packet: Claude native cohort (guided, one command)

Status: prepared, not run. Scope: Claude profile only (Codex stays `not-qualified: not installed`). No
authorization is created here; `executionAuthorization` is false in every output. The qualified verdict is the
founder's, decided from the evidence this cohort saves.

## What is already built and tested offline

`agent_braid/harness_hosts.py` (gate, D2 caps, per-host verdicts), `agent_braid/harness_hosts_native.py` (issued
records, qualified policy, MDRV-04 guard, admit/settle) and `scripts/har_t008_unit.py` (driver) are covered with
deterministic doubles. `scripts/har_t008_lab.py` chains the lab stages in one command. What offline work cannot
produce: real native units on the lab account, real usage readings, a real route and quota observation.

## Preconditions (each needs you; none can be automated)

| # | Precondition | Why it cannot be automated |
|---|---|---|
| 1 | Date is on or after 2026-11-09T20:30Z (founder window) and the weekly usage is at most 80 % after the 2026-11-09T20:00Z reset | The window is your decision; the reading is on claude.ai Usage |
| 2 | The root-owned code copy for the T008 commit exists under `/usr/local/libexec/braid/repo-<short>/` | Needs root; the existing T009 setup script installs it (run by you with `sudo`, as for T009) |
| 3 | The SPEC-065 T009 lab account still has its login and token file in `~/t009/config` | Login is interactive (browser) |
| 4 | Issued records not expired (expires 2026-12-06T18:07:44Z) and no re-qualification trigger fired (macOS build, Claude Code version or hash, profile bytes, catalog, proxy, credential method) | Re-qualification is a founder issuance |

## The one command (in the lab account's own login session)

Preview first, it runs nothing:

    B=/usr/local/libexec/braid
    $B/python312/bin/python3.12 -B -I $B/repo-<short>/scripts/har_t008_lab.py \
        --commit <40-hex> --operator-account <your daily account> --attempt t008-<YYYYMMDD> --plan

Then the same without `--plan`. It re-hashes the pins, runs the dry run (must say `ready`), then the cohort
(at most 4 serial Haiku units). Per unit you type the usage card before and after (5-hour %, weekly %, extra
usage, reset times, plan, route `subscription`). Any D2 stop ends the cohort and is evidence, not a failure to hide.

## Trust basis of the code copy

The wrapper does not wait for a new orchestrator verification record (the T009 `verify-*.json` files are bound to
the T009 attempt). It requires the copy `repo-<short>` and its directories to be root-owned, not writable by
others and not symlinks, and re-hashes `claude`, the interpreter and `sandbox-exec` against the pins of the T009
setup summary. The directory name binds the commit only by convention: before you run it, check that the copy was
installed from the commit named in the PR the orchestrator gives you (the T009 setup script records the commit).

## What you get back

`from-lab/t008-dry-run.json`, `from-lab/t008-cohort-<attempt>.txt` (transcript) and `.json` (final report), each
with a `.sha256`. Aborted, stopped and refused runs also save a report (check its `verdict`); the transcript is kept
even on Ctrl-C. The wrapper exits 0 only for `cohort-finished`. The usage cards are typed by you (self-attested),
and the window and the 80 % weekly stop are enforced by the driver, not the wrapper. Send the report to the orchestrator, which writes `evidence/t008.json` and proposes the
`tasks.md` update. The founder then records the Claude verdict (qualified or not) from the evidence. Codex needs
its own installation and decision; a Claude result never implies both-host acceptance.

## Not done by this packet

No sudo, no braidlab account access, no credentials read, no model spend. The T008 `tasks.md` item stays open.
