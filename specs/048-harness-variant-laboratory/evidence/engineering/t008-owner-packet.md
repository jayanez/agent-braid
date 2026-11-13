# SPEC-048 T008 owner packet: Claude native cohort (headless, guided)

Status: prepared, not run. Scope: Claude profile only (Codex stays `not-qualified: not installed`). No
authorization is created here; `executionAuthorization` is false in every output. The qualified verdict is the
founder's, decided from the evidence this cohort saves.

## What changed on 2026-11-13

SPEC-065 T013 issued new records (`specs/065-native-claude-containment/evidence/qualification/issuance-2026-11-13.json`,
containment `fa59fbae…fa6a`, host `9022b771…847f`, bundle `t009-20261113c`, environment `f0f7617e…e899`, expires
2026-12-13T16:14:45Z). They supersede the 2026-11-06 records, which are void on macOS build 26B131. The environment
hash now includes the session kind: the records hold only in braidlab's own `Background` session, started by root
with `launchctl asuser`, never in a graphical login.

The founder answered two questions (`evidence/founder-decisions-20261113.json`):

- **T008-6** "Mismos términos, nuevos registros (Recommended)": the same terms as on 2026-11-06 (at most 4 serial
  Haiku units, window 2026-11-09T20:30Z to 2026-11-30, D2 caps unchanged, EUR 0, subscription route, readings at
  most 5 minutes old), bound to the 2026-11-13 records. The driver accepts only this founder record (pinned by SHA-256; a test keeps the records it names equal to the ones the driver trusts).
- **T008-7** "Lanzador root sin GUI (Recommended)": a root launcher with a T008 mode. The orchestrator runs its
  `check` automatically; you run `run` in Terminal.app with your password and type the usage readings.

The earlier one-command wrapper `scripts/har_t008_lab.py` ran in braidlab's graphical login. That session kind no
longer matches the records, so it is retired; `scripts/har_t008_launch.sh` replaces it.

## Design

`scripts/har_t008_launch.sh` is a sibling of the SPEC-065 launcher `scripts/har_t009_launch.sh`, not a new mode of
it: the T009 launcher's bytes and its installed copy (`dee6aaf5…1462`) are bound by SPEC-065 T013 evidence, so
editing it would move a qualified, reviewed file. The T008 launcher copies its structure and its helper functions
byte for byte (a test keeps `root_owned`, `auth_status`, `prepare_pub` and `publish` identical), and differs only in:

| | T009 launcher | T008 launcher |
| --- | --- | --- |
| Installed as | `/usr/local/libexec/braid/t009-launch.sh` | `/usr/local/libexec/braid/t008-launch.sh` |
| Modes | `check`, `diag`, `run` | `check`, `run` |
| Label | `t009-YYYYMMDDx` | `t008-YYYYMMDDx` |
| Driver | `har_t009_attempt.py` | `har_t008_unit.py`, its directory checked root-owned |
| `check` | dry run, then self-check | dry run (environment hash against the issued one, window, founder record, D2 caps, units left), then `claude auth status` with the token and an empty config (no model) |
| `run` | at most 3 probe sessions | at most 4 serial units for the whole cohort, counted across labels; a label runs once; Ctrl-C keeps the driver's aborted report in the transcript |
| Publishes to | `/Users/Shared/braid-t009-lab/` | `/Users/Shared/braid-t008-lab/` (`dry-run.json`, `auth.txt`, `run-<attempt>.txt`) |
| Lock | `/usr/local/libexec/braid/.t009-launch.lock` | the same file: no T008 or T009 step starts beside another |

Both run the driver with the same lab paths (`~braidlab/t009/config`, `run`, `arena`), the ones the issued
environment hash was taken with; T008 writes only under `~braidlab/t008/`.

**Four units for the whole cohort.** The driver counts the units each attempt starts in
`~braidlab/t008/out/<attempt>/t008-units.json`, before each launch, and every later attempt subtracts them; a reused
label is refused. So a stopped cohort can be continued under a new label, but never beyond four units in total
(more needs a new founder decision).

**Accepted residuals** (shared with the T009 launcher): a SIGTERM sent by root to `lockf` itself frees the lab lock
while the step continues; anything running as your account can loop the passwordless `check` and so keep the lock
busy (a denial of service, not an escalation). Older code copies under `/usr/local/libexec/braid/repo-*` still
contain drivers that trust the 2026-11-06 records; they are refused by the environment hash (other OS build and
probe catalog) and the T008 launcher never runs them, but remove them at teardown.

## Preconditions (each needs you)

| # | Precondition | Why it cannot be automated |
|---|---|---|
| 1 | Today is inside the window (to 2026-11-30) and the weekly usage is at most 80 % | The reading is on claude.ai Usage |
| 2 | braidlab is logged out of any graphical session (Apple menu, Log Out, in its session) | A graphical braidlab session changes the session kind; the dry run then refuses `environment-drift` |
| 3 | The SPEC-065 lab is as qualified: account, `claude-2.1.292`, `python312`, token file `~braidlab/t009/config/oauth-token` | Any change is a re-qualification trigger (the founder's issuance) |
| 4 | The PR of this packet is merged and the orchestrator names the commit on `develop` it produced (the squash commit) | The installed code copy must be reviewed code |

## Step 1. The orchestrator renders the installer (after the merge)

In its own checkout, read-only. The pins are the SPEC-065 setup pins, the same as in the installed T009 launcher
(`grep -E '^(CLAUDE_SHA256|PYTHON_SHA256|SANDBOX_EXEC_SHA256|OPERATOR_ACCOUNT)=' /usr/local/libexec/braid/t009-launch.sh`);
`COMMIT` is the commit on `develop` that the merge produced.

```sh
COMMIT=<40 hex>; CLAUDE_SHA256=<64 hex>; PYTHON_SHA256=<64 hex>; SANDBOX_EXEC_SHA256=<64 hex>
OPERATOR_ACCOUNT=<the owner's account short name>
git -C <checkout> show "$COMMIT:scripts/har_t008_install.sh" \
  | sed -e "s/@COMMIT@/$COMMIT/" -e "s/@CLAUDE_SHA256@/$CLAUDE_SHA256/" -e "s/@PYTHON_SHA256@/$PYTHON_SHA256/" \
      -e "s/@SANDBOX_EXEC_SHA256@/$SANDBOX_EXEC_SHA256/" -e "s/@OPERATOR_ACCOUNT@/$OPERATOR_ACCOUNT/" \
  > ~/t008-install.sh
chmod 700 ~/t008-install.sh
grep -c '@[A-Z0-9_]*@' ~/t008-install.sh       # 0
shasum -a 256 ~/t008-install.sh                # tell the owner this line
```

## Step 2. You install (Terminal.app, your account, your sudo password)

Check the SHA-256 the orchestrator gave you, then run the installer (no arguments):

```sh
shasum -a 256 ~/t008-install.sh
bash ~/t008-install.sh
```

Every pin and precondition is checked before anything is fetched and before the first `sudo`: the rendered pins,
your account, the hashes of `claude-2.1.292`, the interpreter and `sandbox-exec`, and that
`/usr/local/libexec/braid` and every directory above it are root-owned and closed to others (a passwordless rule may
only name a file nobody else can replace). Then it:

1. fetches the commit from the public repository into a fresh temporary repository (not your checkout, without your
   git configuration), so the copy is exactly the commit's tracked files;
2. stages the root-owned code copy and the launcher rendered from it with the same pins (root:wheel, not writable by
   others) under `/usr/local/libexec/braid/.stage-<short>`;
3. holding the lab lock (refused while a T008 or T009 step runs; no step can start meanwhile), renames the copy to
   `/usr/local/libexec/braid/repo-<short>` and the launcher to `/usr/local/libexec/braid/t008-launch.sh` (0755);
4. writes `/etc/sudoers.d/braid-t008`: your account may run `t008-launch.sh check` as root without a password;
   `run` is not in it. The SPEC-065 rule `/etc/sudoers.d/braid-t009` is left as it is.

It ends with the installed launcher's SHA-256: send that line to the orchestrator. Any `STOP:` line: nothing after
it ran (earlier steps stay done; running it again is safe); tell the orchestrator. Undo: `sudo rm -f /etc/sudoers.d/braid-t008 /usr/local/libexec/braid/t008-launch.sh`
and `sudo rm -r /usr/local/libexec/braid/repo-<short>`.

## Step 3. The orchestrator compares the launcher and runs the check

It renders the expected launcher the same way and compares the SHA-256 with yours; any difference: STOP.

```sh
git -C <checkout> show "$COMMIT:scripts/har_t008_launch.sh" \
  | sed -e "s/@COMMIT@/$COMMIT/" -e "s/@CLAUDE_SHA256@/$CLAUDE_SHA256/" -e "s/@PYTHON_SHA256@/$PYTHON_SHA256/" \
      -e "s/@SANDBOX_EXEC_SHA256@/$SANDBOX_EXEC_SHA256/" -e "s/@OPERATOR_ACCOUNT@/$OPERATOR_ACCOUNT/" \
  | shasum -a 256
sudo -n /usr/local/libexec/braid/t008-launch.sh check t008-YYYYMMDDx   # a label not used before
```

`check` runs the driver's dry run in braidlab's own `Background` session (no Claude session, no quota): pre-flight
with `session-own`, the pinned issuance, the environment hash recomputed there and compared with the issued
`f0f7617e…e899`, the qualified policy, the MDRV-04 guard, the window (a unit must be able to end by 2026-11-30), the
hash-pinned founder record and D2 caps, and the units left (`unitsRemaining`); then
`claude auth status` with the token and an empty temporary config directory (no model call; exit code only). It
publishes `/Users/Shared/braid-t008-lab/dry-run.json` and `auth.txt`. The orchestrator confirms `ready`,
`observed.session.kind` `Background`, `wiring` `ok` and `exit=0` in writing before step 4.

## Step 4. You run the cohort (Terminal.app, only after the orchestrator confirms)

```sh
sudo /usr/local/libexec/braid/t008-launch.sh run t008-YYYYMMDDx
```

`sudo` asks for your password (the rule of step 2 does not cover `run`). The driver asks you to type the attempt
name, then the usage card before the cohort and before and after each unit (5-hour %, weekly %, extra usage, reset
times, plan, route `subscription`; claude.ai Usage or the phone, read right before typing). At most 4 serial units,
one small read-only Haiku session each. Any D2 stop ends the cohort and is evidence, not a failure to hide. Ctrl-C
stops it; the driver's aborted report stays in the transcript. The console output is published as
`/Users/Shared/braid-t008-lab/run-<attempt>.txt`; the last JSON object in it is the driver's report
(`cohort-finished`, `cohort-stopped`, `cohort-aborted` or `refused`). While it runs, every other lab step is
refused. A label runs once: its transcript is kept, and a second `run` with it is refused.

## What you get back and what happens next

`dry-run.json`, `auth.txt` and `run-<attempt>.txt` in `/Users/Shared/braid-t008-lab/`. The usage cards are typed by
you (self-attested). The orchestrator writes `evidence/t008.json` from them and proposes the `tasks.md` update; the
founder then records the Claude verdict (qualified or not). Codex needs its own installation and decision; a Claude
result never implies both-host acceptance, and nothing here admits a SPEC-049/T004 pilot.

## Not done by this packet

No sudo, no braidlab account access, no credentials read, no model spend, no installation. The T008 `tasks.md` item
stays open. Teardown stays the founder's decision (`founder-decisions-20261106.json` T008-5); add
`sudo rm -f /etc/sudoers.d/braid-t008 /usr/local/libexec/braid/t008-launch.sh` and
`sudo rm -rf /Users/Shared/braid-t008-lab` to the SPEC-065 quickstart teardown when it runs (the code copies
under `/usr/local/libexec/braid` go with `sudo rm -r "$BRAID"` there).
