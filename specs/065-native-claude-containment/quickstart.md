# SPEC-065: Quickstart

Implementation in progress: T003 to T008 are done at unit level, the pre-T009 fixes (#979) and the mini delta
re-check (GO for engineering readiness, #985) are merged, and the founder gave a conditional go for T009
(`evidence/founder-decisions-20261103.json`). Nothing native has run. The structural checks and the unit tests
below apply now; the T009 preparation is a checklist, not an authorization.

```sh
python3 -m scripts.validate_spec_kit
python3 -m scripts.validate_change --base develop --profile quick
```

Expected: both pass in a clone without unreachable objects. In a shared-object
worktree the first fails with `public repository contains unreachable objects`;
use a fresh clone as described in `docs/development/SPEC_KIT.md`.

Unit level (deterministic; nothing native runs):

```sh
.venv-speckit/bin/python -m unittest tests.test_harness_manifest tests.test_harness_quota \
  tests.test_harness_transport_claude tests.test_harness_containment_macos \
  tests.test_harness_qualification_probes tests.test_har_t009_attempt -v
```

Expected: all deterministic refusal tests pass; the opt-in live controls
(`BRAID_T007_LIVE_CONTROLS=1`, never set in CI) are skipped.

Operator preparation for T009 (a checklist, not an authorization; it needs the founder go):

- **Install location.** The supervisor runs as the dedicated account, so that account
  must be able to read the repository code, the pinned interpreter and the pinned
  `claude`. The code location cannot be unreadable to it. Install them where the account
  can read but not write (root-owned, outside any operator-private directory), and give
  the account no read access to the operator's home. Dedicated-user-owned ancestors pass
  the executable check but leave a hash-to-exec window (a root-owned install is stronger).
- **`interpreter_root`.** It is readable and map-executable inside the sandbox, so use a
  minimal prefix that holds only the interpreter and its standard library, never a
  repository or a home directory.
- **Account hygiene the code cannot see.** The account check refuses admin/wheel, a system account
  (uid below 500), the operator's own account (`--operator-account`, compared by uid; RV-16 as amended on
  2026-11-03, the owner of `/dev/console` is no longer examined) and a loose home. It does not see sudoers rules by name, ACL grants or
  groups such as `_developer`; the operator verifies those.
- **`config_dir`.** Use a dedicated, empty or small directory, never a home directory or a shared
  cache, and check its entry count and size before every attempt. The disk bound counts what is
  already in it (no baseline), so a large or pre-used `config_dir` makes every run refuse with
  `disk-limit-exceeded`, including the pre-session subset. Investigate that refusal as an
  environment problem before the next attempt; it is not a probe finding. The before/after
  listing hashes up to 500 files with no per-file size cap, so a very large file slows it (MDRV-03).
- **Session.** Run the supervisor inside the dedicated user's own login session, not
  through `sudo -u` from the operator's session, and expect failed probe controls to be
  recorded as findings.
- **Entry point.** `scripts/har_t009_attempt.py` is the only supported entry point: it builds the T005
  backend, the T006 transport factory and `make_qualification_runner` itself (account home as `real_home`,
  credential scan of `config_dir`, before/after listing of `config_dir`, launch profile on). Do not call the
  runner by hand, pass `runner_options`, or use `launch_profile=False`. Run it only as the dedicated account:
  the arena plants decoys in the home it resolves.
- **Bundle.** Review it for local identifiers before committing it.

Qualification attempt (T009, only after founder decisions and ADR acceptance): run the driver as described
in "Operator setup for T009", inspect `evidence/qualification/<attempt>/summary.json`, and hand the bundle to
the issuer. Expected: either every effect `enforced` and HOST-01 complete, or a retained not-qualified bundle.
Neither outcome is a failure of the procedure.

## Operator setup for T009

This is the founder's runbook for the conditional go recorded in
`evidence/founder-decisions-20261103.json`, as amended by `evidence/founder-decisions-20261103b.json` and confirmed on 2026-11-04 by `evidence/founder-decisions-20261104b.json`. It is a checklist, not an authorization:
`executionAuthorization` stays `false`, issuance stays T010 (NC-9). The order is fixed:

1. you run steps 0 to 8 (step 0 is a check; the rest use sudo, in your own session) with `scripts/har_t009_setup.py`, only after the orchestrator confirms the re-check of the 2026-11-03 decisions is a GO;
2. you switch to the dedicated account and run steps 9 to 11 in its own login session with `scripts/har_t009_lab.py` (login, driver `--dry-run`,
   self-check and the real attempt, waiting for the orchestrator's verification files between them);
3. you send the dry-run output to the orchestrator, which verifies it as evidence;
4. only after the orchestrator confirms, step 11 (the real attempt: at most 3 small Haiku sessions).

> **Founder decisions of 2026-11-03** (`evidence/founder-decisions-20261103b.json`): the backend accepts the whole
> macOS 27.x series (NC-3); the dedicated account is no longer refused for owning `/dev/console`, and is
> refused instead when it is the founder's own account, in admin or wheel, or a system account (RV-16, rule
> change); you type the quota readings, taken on claude.ai Usage or on the phone (NC-6, self-attested). The
> driver builds its attempt records in memory only; they are not issuance (NC-9). These decisions need the
> re-check in `evidence/recheck-t009-unblock.md`, and the orchestrator confirms in writing that it is a GO
> before you start step 1.

Nothing native (`claude`, `sandbox-exec`, the network) runs before step 9 (the login). The sandbox and
the sessions run only in step 11. If any command fails or prints something other than described, stop
and tell the orchestrator; do not improvise. `COMMIT` below is the full commit the orchestrator names (it
must contain `scripts/har_t009_attempt.py`); replace the quoted `PASTE_...` text with it. A line that ends
in `STOP` means: do not continue.

> **Founder go of 2026-11-04** (`evidence/founder-decisions-20261104b.json`): "Go pero quiero que prepares tú el runbook
> para que todo sea completamente automatizado", and then "vamos a seguir con los pasos, pero automatiza todo lo
> que puedas para que sólo tenga que cambiar de usuario y lanzar un script". So the runbook is two scripts and a
> verification helper. They are not an authorization. Every check of the runbook is a hard stop in them (same
> `STOP:` text where the runbook has one) and they add only safety stops of their own. They do not replace the
> orchestrator: the lab script WAITS for a verification file the orchestrator writes from your account after it
> verified the setup summary, the dry run and the self-check, and it refuses a missing or mismatching one. They do
> not touch the NC-6 readings: the driver asks you to type them, exactly as in step 11. `executionAuthorization`
> stays false and issuance stays T010 (NC-9).

### Run it with the scripts: one script in your account, one in the lab account

**(a) In your own account (steps 0 to 8, plus the handoff directory).** `COMMIT` is the full commit the
orchestrator names; it must contain `scripts/har_t009_attempt.py`, `har_t009_setup.py`, `har_t009_lab.py` and
`har_t009_verify.py`. Run it from your checkout at that commit, not as root:

```sh
COMMIT='PASTE_THE_40_CHARACTER_COMMIT_FROM_THE_ORCHESTRATOR'
python3 scripts/har_t009_setup.py --commit "$COMMIT" --dry-run   # prints every command and check, runs none
python3 scripts/har_t009_setup.py --commit "$COMMIT"             # your sudo password, then the braidlab password
```

You type two things: your sudo password (asked up front; it may ask again if its timestamp expires during a slow
step) and the new account's password at the `sysadminctl` prompt (`-password -`, it never goes through the
script). Nothing native runs (`claude`, `sandbox-exec`, the network). On a failed check it prints the runbook's
`STOP:` line and a failed command prints its first error lines; exit 1: fix the cause or tell the orchestrator.
Re-running is safe where the runbook allows it: an existing account is kept and re-checked, installs overwrite
their copy, the code copy is rebuilt. The empty `config_dir` check of step 7 is kept as written, so a re-run after
the lab login stops there. Reinstalling the code copy after a fix ("Before step 10b" below) is therefore not a
re-run: use the manual commands of step 5, write a new summary by hand, and tell the orchestrator.

It creates the **handoff directory** `/Users/Shared/braid-t009/` (`--handoff` to change it), owned by you, mode 755:

| Path | Owner / mode | Who writes | Content |
| --- | --- | --- | --- |
| `to-lab/` | you, 755 | you and the orchestrator | `setup-summary.json`, `verify-setup.json`, `verify-dry-run.json`, `verify-self-check.json` |
| `from-lab/` | `braidlab:staff`, 750 | the lab script | `dry-run.json`, `self-check.json` (+ `.sha256` each), `bundle-<attempt>/` and its listing |

The lab account can read `to-lab/` but cannot write it: that is what makes a verification file trustworthy. You
read `from-lab/` through the `staff` group; to remove it use `sudo rm -r` (see the teardown). Nothing in it is a
secret, but the bundle holds local identifiers: review it before committing it.

Its last output, and `to-lab/setup-summary.json`, is a JSON summary: the claude copy hash, the interpreter and
`sandbox-exec` hashes, the codesign `TeamIdentifier`, the code copy's listing hash and git tree, and your home
mode before step 6. **Paste that JSON to the orchestrator**. Options: `--account`, `--checkout`, `--claude-src`,
`--python-src`, `--handoff`.

**(b) In the `braidlab` login session (steps 9 to 11).** Switch user (fast user switching, step 9 below), open
Terminal and run the one lab script with the pinned interpreter from the root-owned code copy (`<short>` is the first
7 characters of `COMMIT`; `OPERATOR_ACCOUNT` is your daily account, `id -un` in your session; `ATTEMPT` is the label
the orchestrator gave you):

```sh
B=/usr/local/libexec/braid
$B/python312/bin/python3.12 -B -I $B/repo-<short>/scripts/har_t009_lab.py \
    --commit <COMMIT> --operator-account <OPERATOR_ACCOUNT> --attempt <ATTEMPT> --plan   # prints the stages, runs none
$B/python312/bin/python3.12 -B -I $B/repo-<short>/scripts/har_t009_lab.py \
    --commit <COMMIT> --operator-account <OPERATOR_ACCOUNT> --attempt <ATTEMPT>
```

What it does, in order, each stage a hard stop:

1. reads `to-lab/setup-summary.json` (commit must equal `--commit`) and re-hashes `claude`, the interpreter and
   `sandbox-exec` against its pins;
2. **waits** for `to-lab/verify-setup.json` (bound to the summary's SHA-256; the orchestrator checks the claude hash
   against the published release checksum before step 9);
3. step 9: no `ANTHROPIC`/`CLAUDE` variable (names or values), then `claude auth login` (the browser login is yours;
   `--skip-login` if already logged in) and the check that `config_dir` holds a few small files;
4. step 10: the driver `--dry-run`, saved to `from-lab/dry-run.json` with its SHA-256; must be `ready`; **waits** for
   `to-lab/verify-dry-run.json`;
5. step 10b: the driver `--self-check --founder-go`, saved to `from-lab/self-check.json` with its SHA-256; must be
   `self-check-ok`; **waits** for `to-lab/verify-self-check.json`;
6. step 10c: refuses an attempt label whose output directory already holds a session counter (a new label from the
   orchestrator, or `--resume` for a crashed run of the same label; NC-10);
7. step 11: the driver `--founder-go` with your terminal attached. **The driver asks you** to type the attempt name
   and, before and after each of at most three sessions, the usage card (claude.ai Usage or the phone: 5-hour %,
   weekly %, extra usage, and the time or `now`), self-attested (NC-6). The script does not read, fake or skip them;
   the session budget (NC-10) and all the quota stops are the driver's. Afterwards the output directory is *copied*
   to `from-lab/bundle-<attempt>/` with a SHA-256 listing (the driver's printed `bundleSha256` stays the authoritative
   bundle hash: keep the console output).

A verification file counts only if it is owned by you (not the lab account), is not group/world writable, sits in a
directory the lab account cannot write, and carries the stage, commit, attempt, the verdict `approved` and the SHA-256
of the exact subject. A missing one is waited for (`--wait-timeout`, default 7200 s, `--poll`); a mismatching,
rejected or tampered one stops the script. The script prints the subject SHA-256 while it waits. Exit codes: 0, the
driver's own code for the real attempt, 1 for its own `STOP:`.

**(c) The orchestrator, from your account, between the two.** `scripts/har_t009_verify.py` (read-only apart from the
approval file; no `claude`, `sandbox-exec` or network) checks one artifact and writes `to-lab/verify-<stage>.json`:

```sh
python3 scripts/har_t009_verify.py setup --commit <COMMIT> --attempt <ATTEMPT> --published-claude-sha256 <64 hex>
python3 scripts/har_t009_verify.py dry-run --commit <COMMIT> --attempt <ATTEMPT>
python3 scripts/har_t009_verify.py self-check --commit <COMMIT> --attempt <ATTEMPT>
```

- `setup`: the summary is `har-t009-setup-v1` for this commit with `nativeRun` and `executionAuthorization` false;
  the claude hash equals the **published release checksum passed in** (an independent source, not read from the
  machine) and the installed copy re-hashes to it; `codesign --verify --strict --deep` passes and shows
  `TeamIdentifier=Q6L2SF6YDW` with the Anthropic Developer ID authority; the interpreter and `sandbox-exec` re-hash to
  their pins; the code copy listing recomputes to the summary's.
- `dry-run`: the file's SHA-256 equals the lab's recorded one; verdict `ready`, no failed check, the right attempt,
  `nativeRun` false, `dryRun` true, `executionAuthorization` false.
- `self-check`: SHA-256 as above; verdict `self-check-ok`, the right attempt, `executionAuthorization` false.

Limit: the lab account can run the driver by hand and can write `from-lab/`, so this handshake guards against skipped
stages and accidents, not against a hostile lab account; the verification binds what the orchestrator saw to a
SHA-256. The driver's JSON has no commit field, so the dry run and the self-check are tied to the commit through the
setup summary and the pinned hashes only. A failed check writes a `rejected` file listing what failed (exit 1) and the lab script stops. The helper approves
evidence, it does not authorize anything: the orchestrator still reads the dry run and the self-check itself.


### Reference: the manual commands for steps 0 to 8 (what the script runs, and the undo)

Variables, in your own terminal (not root):

```sh
ACCT=braidlab
BRAID=/usr/local/libexec/braid
COMMIT='PASTE_THE_40_CHARACTER_COMMIT_FROM_THE_ORCHESTRATOR'
printf %s "$COMMIT" | grep -Eq '^[0-9a-f]{40}$' || { echo "STOP: COMMIT is not a 40-character hash"; false; }
SHORT=${COMMIT:0:7}
CLAUDE_SRC=/opt/homebrew/Caskroom/claude-code/2.1.292/claude
PY_SRC="$HOME/.local/share/uv/python/cpython-3.12.13-macos-aarch64-none"
CHECKOUT="$HOME/Repos/Personal/agent-braid"   # your checkout, only to export the code at $COMMIT
```

**Step 0. Check the macOS series (no sudo).**

```sh
sw_vers -productVersion        # must start with 27. (27.2 here is fine, NC-3); anything else: STOP
```

**Step 1. Create the standard account and close its home.** `sysadminctl -addUser` without `-admin` makes a standard
account with its own home. `-password -` makes it ask for the password on the terminal, so it never
lands in your shell history. Pick a password you do not reuse.

```sh
sudo sysadminctl -addUser "$ACCT" -fullName "Braid Lab" -password -
id "$ACCT"                                           # no group 80 (admin) and no group 0 (wheel)
dseditgroup -o checkmember -m "$ACCT" admin          # must say "no"
test -d /Users/"$ACCT" || sudo createhomedir -c -u "$ACCT"   # only creates the home if it is missing
sudo chown "$ACCT":staff /Users/"$ACCT" && sudo chmod 700 /Users/"$ACCT"
stat -f '%Su %Sg %Lp' /Users/"$ACCT"                 # must print: braidlab staff 700
```

The driver and the backend refuse an account home with any group or other permission bit
(`account-home-private`); a new home is usually 750, so the `chmod 700` is required.

Undo: `sudo sysadminctl -deleteUser "$ACCT"`, then `ls /Users` (if the home is still there,
`sudo rm -r /Users/braidlab`).

**Step 2. Create the root-owned install directory.** The pinned files live here, root-owned and
read-only for braidlab (RV-22).

```sh
sudo install -d -o root -g wheel -m 755 "$BRAID"
ls -ld /usr/local /usr/local/libexec "$BRAID"        # all root:wheel, no group/other write
```

Undo: `sudo rm -r "$BRAID"` (and `/usr/local/libexec` only if it was empty and you created it).

**Step 3. Install the pinned `claude` copy.** The Homebrew copy is owned by you, so the backend would
refuse it. This copies the exact 2.1.292 binary; it does not run it.

```sh
sudo install -o root -g wheel -m 755 "$CLAUDE_SRC" "$BRAID/claude-2.1.292"
shasum -a 256 "$CLAUDE_SRC" "$BRAID/claude-2.1.292"  # the two hashes must be identical; keep it
ls -l "$BRAID/claude-2.1.292"                        # -rwxr-xr-x root wheel
for f in "$CLAUDE_SRC" "$BRAID/claude-2.1.292"; do
  codesign --verify --strict --deep "$f" && echo "signature valid: $f"
  codesign -dv --verbose=2 "$f" 2>&1 | grep -E '^(Authority|TeamIdentifier)='
done
```

Both files must print `signature valid` and the same `TeamIdentifier=Q6L2SF6YDW` with an
`Authority=Developer ID Application: Anthropic PBC (Q6L2SF6YDW)` line. Anything else, or a failed
verify: STOP; the copy is not the Anthropic build. Comparing the two hashes only shows the copy equals
the source, so send the hash to the orchestrator, who checks it against a digest from an independent
source (the published release checksum) and records it in the founder evidence **before step 9**,
because step 9 runs this file outside the sandbox.

Undo: `sudo rm "$BRAID/claude-2.1.292"`.

**Step 4. Install a minimal root-owned interpreter prefix.** `interpreter_root` is readable and
map-executable inside the sandbox, so it holds only the interpreter and its standard library (a copy of
the standalone CPython 3.12 that `uv` installed for you), never a repository or your home.

```sh
sudo install -d -o root -g wheel -m 755 "$BRAID/python312/bin" "$BRAID/python312/lib"
sudo install -o root -g wheel -m 755 "$PY_SRC/bin/python3.12" "$BRAID/python312/bin/python3.12"
sudo ditto "$PY_SRC/lib/python3.12" "$BRAID/python312/lib/python3.12"
sudo find "$BRAID/python312" -name __pycache__ -prune -exec rm -r {} +
sudo chown -R root:wheel "$BRAID/python312" && sudo chmod -R go-w "$BRAID/python312"
sudo find "$BRAID/python312" -not -user root                       # must print nothing
shasum -a 256 "$BRAID/python312/bin/python3.12"                    # keep it
```

Undo: `sudo rm -r "$BRAID/python312"`.

**Step 5. Install a root-owned copy of the repository code at the stated commit.** `git archive`
exports the tracked files only (no `.git`, no history, none of your local files).

```sh
git -C "$CHECKOUT" archive --prefix="repo-$SHORT/" "$COMMIT" | sudo tar -x -C "$BRAID" --no-same-owner
sudo chown -R root:wheel "$BRAID/repo-$SHORT" && sudo chmod -R go-w,a+rX "$BRAID/repo-$SHORT"
sudo find "$BRAID/repo-$SHORT" -not -user root                     # must print nothing
ls "$BRAID/repo-$SHORT/scripts/har_t009_attempt.py"
```

Undo: `sudo rm -r "$BRAID/repo-$SHORT"`.

**Step 6. Close your home to the new account.** Your home is mode 750 with group `staff` on this
machine, and the new account's primary group is `staff`, so it could list your files. `700` closes that.

```sh
stat -f '%Lp' "$HOME"          # note the current mode (750 when checked on 2026-11-03)
chmod 700 "$HOME"
```

Undo: `chmod 750 "$HOME"` (the value you noted).

**Step 7. Create the account's private working directories.** The empty `config_dir` (its own
`CLAUDE_CONFIG_DIR`), the run root, the arena parent and the output directory, owned by braidlab, mode
700, in its home. Step 1 created and closed the home; this guard stops if that did not happen.

```sh
[ "$(stat -f '%Su %Lp' /Users/"$ACCT")" = "$ACCT 700" ] || { echo "STOP: step 1 (home mode 700) not done"; false; }
for d in config run arena out; do
  sudo install -d -o "$ACCT" -g staff -m 700 "/Users/$ACCT/t009/$d"
done
sudo chown "$ACCT":staff "/Users/$ACCT/t009" && sudo chmod 700 "/Users/$ACCT/t009"
sudo ls -la "/Users/$ACCT/t009/config"                              # empty
```

Undo: `sudo rm -r "/Users/$ACCT/t009"`.

**Step 8. Record the pins.** You paste the three hashes into step 10; the orchestrator recomputes
them itself from the dry-run.

```sh
shasum -a 256 "$BRAID/claude-2.1.292" "$BRAID/python312/bin/python3.12" /usr/bin/sandbox-exec
```

> The manual steps 9 to 11 below are the reference (and the fallback) for what `har_t009_lab.py` runs.

**Step 9. Switch to the account's own login session and log in to Claude.** Use fast user switching
(the user name in the menu bar, or Lock Screen, then "Switch User"), log in as `braidlab` (skip the
Apple ID and any other sign-in offers), open Terminal there. Do not use `sudo -u`. This is the NC-5
login: the account's own `CLAUDE_CONFIG_DIR`, its own keychain, no secret copied from you. It is the
first native run, and it happens outside the sandbox on purpose.

```sh
env | grep -i -E 'ANTHROPIC|CLAUDE' || true          # must print nothing
export CLAUDE_CONFIG_DIR="$HOME/t009/config" DISABLE_AUTOUPDATER=1
/usr/local/libexec/braid/claude-2.1.292 auth login   # log in with the subscription account in the browser
ls -la "$CLAUDE_CONFIG_DIR"                          # a few small files (a fresh login), nothing big
```

Undo: `claude auth logout` with the same `CLAUDE_CONFIG_DIR`, and revoke the session in the Claude
account settings; deleting the account (teardown) removes its keychain.

**Step 10. Dry run in the braidlab session.** Pre-flight only: no sandbox, no `claude`, no network. It
prints a JSON verdict, `ready` or `refused` with the failed checks and a fix hint for each, and exits 0
or 2. Paste the quoted values first (from the orchestrator, from step 8, and your own account short name,
which `id -un` prints in your own session); the checks below stop you if one is wrong. The driver must run with the pinned interpreter and `-B -I`; any other Python is refused.

```sh
BRAID=/usr/local/libexec/braid
COMMIT='PASTE_THE_40_CHARACTER_COMMIT_FROM_THE_ORCHESTRATOR'
CLAUDE_SHA256='PASTE_64_HEX_FROM_STEP_8_CLAUDE'
PYTHON_SHA256='PASTE_64_HEX_FROM_STEP_8_PYTHON'
SANDBOX_EXEC_SHA256='PASTE_64_HEX_FROM_STEP_8_SANDBOX_EXEC'
printf %s "$COMMIT" | grep -Eq '^[0-9a-f]{40}$' || { echo "STOP: COMMIT is not a 40-character hash"; false; }
for h in "$CLAUDE_SHA256" "$PYTHON_SHA256" "$SANDBOX_EXEC_SHA256"; do
  printf %s "$h" | grep -Eq '^[0-9a-f]{64}$' || { echo "STOP: a hash is not pasted correctly"; false; }
done
SHORT=${COMMIT:0:7}
PYRUN=("$BRAID/python312/bin/python3.12" -B -I "$BRAID/repo-$SHORT/scripts/har_t009_attempt.py")
OPERATOR_ACCOUNT='PASTE_YOUR_OWN_ACCOUNT_SHORT_NAME'   # your daily account; "id -un" in your own session
printf %s "$OPERATOR_ACCOUNT" | grep -Eq '^[a-z_][a-z0-9_-]{0,31}$' || { echo "STOP: OPERATOR_ACCOUNT is not an account name"; false; }
ATTEMPT='t009-20261104'   # the attempt label the orchestrator gave you; a new label (and out dir) after attempt 1, see step 10c
printf %s "$ATTEMPT" | grep -Eq '^t009-[0-9]{8}[a-z0-9-]{0,16}$' || { echo "STOP: ATTEMPT is not an attempt label"; false; }
ARGS=(--attempt "$ATTEMPT" --operator-account "$OPERATOR_ACCOUNT"
  --claude "$BRAID/claude-2.1.292" --claude-sha256 "$CLAUDE_SHA256"
  --interpreter "$BRAID/python312/bin/python3.12" --interpreter-sha256 "$PYTHON_SHA256"
  --interpreter-root "$BRAID/python312" --sandbox-exec-sha256 "$SANDBOX_EXEC_SHA256"
  --config-dir "$HOME/t009/config" --run-root "$HOME/t009/run"
  --arena-parent "$HOME/t009/arena" --out-dir "$HOME/t009/out/$ATTEMPT")
"${PYRUN[@]}" "${ARGS[@]}" --dry-run | tee "$HOME/t009/dry-run.json"
cp "$HOME/t009/dry-run.json" /Users/Shared/t009-dry-run.json
```

Check that the verdict names your own daily account as the operator account (not another user's, and not
the braidlab account): the code can only prove it differs from the lab account, not that it is yours. Then
tell the orchestrator that `/Users/Shared/t009-dry-run.json` exists. A `refused` verdict is not a
failure of the procedure: it names what to fix. Do not continue to step 11 until the orchestrator
confirms in writing that the verdict is `ready` and matches the pins it recomputed.

**Before step 10b: the code changed after attempt 1.** The fix of 2026-11-04 edits
`harness_qualification_probes.py`, and the catalog hash binds that file's bytes, so the catalog and
environment hashes moved. Before step 10b you need the orchestrator's new `COMMIT` pin, step 5 redone with
it (`repo-$SHORT` is the installed copy the pre-flight checks), the variable block of step 10 updated with
that `COMMIT`, and a fresh step 10 dry run that the orchestrator confirmed as `ready`. With the old copy or
the old dry run the self-check's pre-flight refuses with a hash mismatch.

**Step 10b. Self-check (after the dry run, before step 11; added after attempt 1 of 2026-11-03).** The
real run refuses a session when the backend's own pre-session check fails, and by then a session is
counted. `--self-check` runs that check alone, built exactly like the real run, so a failure shows
here and costs nothing. It needs `--founder-go` because it does run native things under the sandbox:
the pinned `claude --version` (once for the launch profile and once per F4 probe under the
`launch-probe` profile; no session, no prompt, no login, no network), the five F4 fixtures with the
interpreter (FS-01, NET-01, CRED-01, PROC-01, NET-06), and, for NET-06 only, one TLS handshake with the
allowed endpoint through the local proxy (no request, no credential). It reserves no session, asks for
no usage reading and no typed name, and writes no counter and no bundle.

```sh
"${PYRUN[@]}" "${ARGS[@]}" --self-check --founder-go | tee "$HOME/t009/self-check.json"
cp "$HOME/t009/self-check.json" /Users/Shared/t009-self-check.json
```

It prints a JSON verdict and exits 0 (`self-check-ok`) or 2. In `preSessionCheck` every F4 probe shows
its `expected` and `observed` verdict (`allowed`, `denied`, `error` or `not-run`); `compileCheck` is
`exec-denied` when the profile compiled, denied a non-listed exec and ran a listed one; `refusal` is the
backend's fixed reason code and `stage` says where it stopped (`mechanism-or-workspace`,
`compile-check` or `f4-probes`). After a refusal the probes the check did not reach are run one by
one and marked `"supplementary": true` (after `self-check-allowed`, an escape, they are not run and show
`not-run`), and `backendRefusals` lists the refusals of the nested runs
(entry `fixture`, `launch` or `launch-probe` and the fixed reason code). Nothing printed is a
path, account name, hash or value. Tell the orchestrator that `/Users/Shared/t009-self-check.json`
exists. Do not continue to step 11 unless the verdict is `self-check-ok` and the orchestrator
confirms it in writing. A `self-check-refused` is a finding, not a failure of the procedure.

**Step 10c. The attempt label for the real run.** The output directory of attempt 1
(`$HOME/t009/out/t009-20261104`) holds `.sessions.json` with `sessionsStarted: 1` and
`quotaStop: session-refused-self-check-failed`. Running step 11 with that same `ATTEMPT` resumes the stop
and refuses every session, so it cannot work. Do not delete or edit that file. Whether a refused session
counts against the budget of three, and whether to archive the old directory and start a new one, is
decided by you with the orchestrator (NC-10). Only when the orchestrator names a new attempt label,
set `ATTEMPT` to it in the variable block of step 10, run step 10 again (dry run, confirmed `ready`) and then step 11.
If the orchestrator says to continue the old attempt, `ATTEMPT` stays as it is and the sessions will be refused: then stop
and send the output.

**Step 11. The real attempt (only after the orchestrator confirms).** The same command with
`--founder-go` instead of `--dry-run`. If you closed the terminal after step 10, run its variable block
(from `BRAID=` to the `ARGS=(...)` line, `OPERATOR_ACCOUNT` included) again first.

```sh
"${PYRUN[@]}" "${ARGS[@]}" --founder-go
cp -R "$HOME/t009/out/$ATTEMPT" "/Users/Shared/t009-bundle-$ATTEMPT"
```

It asks you to type the attempt name, then, before and after each of at most three sessions, for the
usage card (read on claude.ai Usage or on the phone, same Claude account): 5-hour %, weekly %, whether extra usage is on, and the time you read it.
Answer `now` right after reading it (or type `HH:MM:SS`; `HH:MM` can collide with the next reading in the
same minute). A typo is asked again up to three times. A reading older than five minutes, a missing one, a
start at 90 % or more of the 5-hour window, or a session that used more than 2 points stops the attempt.
The values are typed by you, so they are operator-attested. At the end it prints the bundle SHA-256.

If it ends with a JSON `"verdict": "error"` instead, keep that output: it says how many sessions were
spent (`quota.started`). The session counter stays in the output directory, so a re-run with the same
`--out-dir` continues the budget of three sessions (a new attempt name does not reset it). Send the output
to the orchestrator before trying again. If the sessions end as `quota-stop` one after another,
the old counter is being resumed: stop and send the output (step 10c).

**If step 11 fails.** Keep the whole JSON, the console text above it and the output directory exactly as
they are; do not delete, edit or move anything in the output directory (the session counter
`.sessions.json` is the NC-10 budget), and do not run step 11 again before the orchestrator says so.
The error verdict can carry these fields, none of which holds a secret or a value:

- `reason`: the exception and its fixed reason code, for example `ProbeError: secret-in-artifact`.
- `quota.started`: sessions counted; `nativeRun` is `true` because the helper probes run natively with
  or without a session.
- `scan` (a refused bundle only): `findings`, each with the `file` (`results.jsonl`, `quota.json`,
  `environment.json`, `catalog.json` or `summary.json`), the `line`, the JSON `path` (for example
  `$.machNames[17]`; `<key>` stands for a key that is not a plain field name), the `rule`
  (`listed-literal`, `long-run`, `anthropic-api-key`, `jwt`, `pem-header`, `github-token` or
  `aws-access-key-id`) and the match `length`. For a `listed-literal` the `origin` says which list it came
  from (`caller`, `marker`, or `credential#N`) and, for a credential, `source` names the file and field of
  the account's own config that holds it (for example `.claude.json`, `$.oauthAccount.billingType`). The
  value is never printed. `total` counts every finding; at most 20 are listed. A refused bundle writes no
  bundle file; only the counter stays.
- `preSessionEvidence`: the backend's refusals (`entry`, fixed `refused` code, `compileCheck`, and the F4
  probes' `expected`/`observed` verdicts), the same vocabulary as step 10b.

The counter matters for the next run. After a session that the backend refused before launching
anything, the counter holds `sessionsStarted: 1` and a `quotaStop` such as
`session-refused-self-check-failed`, and a re-run with the same `--out-dir` resumes that stop: it
would refuse every remaining session (`quota-stop`) and write a bundle with the three session probes
inconclusive. Whether such a refused session still counts against the budget of three, and
whether the counter may be archived into the evidence and restarted in a new `--out-dir`, is a decision
of the founder with the orchestrator (NC-10); do not decide it by deleting the file.

Then, back in your own session, take ownership of the copy (`sudo chown -R "$USER"
"/Users/Shared/t009-bundle-$ATTEMPT"`), review the bundle for local identifiers and copy it to
`specs/065-native-claude-containment/evidence/qualification/<attempt>/`.

### Teardown (after the bundle is copied)

```sh
rm -r "/Users/Shared/t009-bundle-$ATTEMPT" /Users/Shared/t009-dry-run.json /Users/Shared/t009-self-check.json /Users/Shared/t009-setup-summary.json
sudo rm -r /Users/Shared/braid-t009              # the handoff directory of the scripts (from-lab/ is the lab account's)
# log out of braidlab (Apple menu, Log Out) and revoke its Claude session in the account settings
sudo sysadminctl -deleteUser "$ACCT"           # removes the account, its home and its keychain
ls /Users                                      # braidlab gone (else: sudo rm -r /Users/braidlab)
sudo rm -r "$BRAID"                            # claude copy, interpreter prefix, code copy
chmod 750 "$HOME"                              # the mode you noted in step 6
dscl . -list /Users | grep -c "^$ACCT\$"       # 0
```
