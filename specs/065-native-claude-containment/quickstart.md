# SPEC-065: Quickstart

Implementation in progress: T003 to T008 are done at unit level, the pre-T009 fixes (#979) and the mini delta
re-check (GO for engineering readiness, #985) are merged, and T009 awaits the founder go. The structural
checks and the unit tests below apply now; the T009 preparation is a checklist, not an authorization.

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
  tests.test_harness_qualification_probes -v
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
- **Account hygiene the code cannot see.** The account check refuses admin/wheel, the
  console user and a loose home. It does not see sudoers rules by name, ACL grants or
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
- **Entry point.** Use `make_qualification_runner`: `real_home` is the account's home
  (a runner without one is refused), the credential scan reads `config_dir`, and each
  probe session records a before/after listing of `config_dir` (names and digests).
  Do not pass `runner_options` that replace the executors or weaken the pre-session check, and
  do not use `launch_profile=False` in `make_f4_probe_runner`. Run it only as the dedicated
  account: the arena plants decoys in the home it resolves.
- **Bundle.** Review it for local identifiers before committing it.

Qualification attempt (T009, only after founder decisions and ADR acceptance):
run the probe runner for the decided configuration, inspect
`evidence/qualification/<attempt>/summary.json`, and hand the bundle to the
issuer. Expected: either every effect `enforced` and HOST-01 complete, or a
retained not-qualified bundle. Neither outcome is a failure of the procedure.

## Operator setup for T009

This is the founder's runbook for the conditional go recorded in
`evidence/founder-decisions-20261103.json`. It is a checklist, not an authorization:
`executionAuthorization` stays `false`, issuance stays T010 (NC-9). The order is fixed:

1. you run steps 1 to 8 (sudo, in your own session);
2. you switch to the dedicated account and run steps 9 and 10 in its own login session (login, then the
   driver `--dry-run`);
3. you send the dry-run output to the orchestrator, which verifies it as evidence;
4. only after the orchestrator confirms, step 11 (the real attempt: at most 3 small Haiku sessions).

Nothing native (`claude`, `sandbox-exec`, the network) runs before step 9 (the login). The sandbox and
the sessions run only in step 11. If any command fails or prints something other than described, stop
and tell the orchestrator; do not improvise. Replace `<COMMIT>` with the commit the orchestrator names
(it must contain `scripts/har_t009_attempt.py`).

Variables, in your own terminal (not root):

```sh
ACCT=braidlab
BRAID=/usr/local/libexec/braid
COMMIT=<COMMIT>                       # full 40-character commit from the orchestrator
SHORT=${COMMIT:0:7}
CLAUDE_SRC=/opt/homebrew/Caskroom/claude-code/2.1.292/claude
PY_SRC="$HOME/.local/share/uv/python/cpython-3.12.13-macos-aarch64-none"
CHECKOUT="$HOME/Repos/Personal/agent-braid"   # your checkout, only to export the code at $COMMIT
```

**Step 1. Create the standard account.** `sysadminctl -addUser` without `-admin` makes a standard
account with its own home. `-password -` makes it ask for the password on the terminal, so it never
lands in your shell history. Pick a password you do not reuse.

```sh
sudo sysadminctl -addUser "$ACCT" -fullName "Braid Lab" -password -
id "$ACCT"                                           # no group 80 (admin) and no group 0 (wheel)
dseditgroup -o checkmember -m "$ACCT" admin          # must say "no"
ls -ld /Users/"$ACCT"                                # a home exists, owned by braidlab
```

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
```

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
700, in its home. If `/Users/braidlab` does not exist yet, log in as braidlab once first.

```sh
for d in config run arena out; do
  sudo install -d -o "$ACCT" -g staff -m 700 "/Users/$ACCT/t009/$d"
done
sudo chown "$ACCT":staff "/Users/$ACCT/t009" && sudo chmod 700 "/Users/$ACCT/t009"
sudo ls -la "/Users/$ACCT/t009/config"                              # empty
```

Undo: `sudo rm -r "/Users/$ACCT/t009"`.

**Step 8. Record the pins.** You paste them into the driver command; the orchestrator recomputes
them itself from the dry-run.

```sh
shasum -a 256 "$BRAID/claude-2.1.292" "$BRAID/python312/bin/python3.12" /usr/bin/sandbox-exec
```

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
prints a JSON verdict, `ready` or `refused` with the failed checks, and exits 0 or 2.

```sh
BRAID=/usr/local/libexec/braid; SHORT=<SHORT>        # the same 7 characters as above
"$BRAID/python312/bin/python3.12" -B -I "$BRAID/repo-$SHORT/scripts/har_t009_attempt.py" \
  --attempt t009-20261104 \
  --claude "$BRAID/claude-2.1.292" --claude-sha256 <CLAUDE_SHA256> \
  --interpreter "$BRAID/python312/bin/python3.12" --interpreter-sha256 <PYTHON_SHA256> \
  --interpreter-root "$BRAID/python312" --sandbox-exec-sha256 <SANDBOX_EXEC_SHA256> \
  --config-dir "$HOME/t009/config" --run-root "$HOME/t009/run" \
  --arena-parent "$HOME/t009/arena" --out-dir "$HOME/t009/out/t009-20261104" \
  --dry-run | tee "$HOME/t009/dry-run.json"
cp "$HOME/t009/dry-run.json" /Users/Shared/t009-dry-run.json
```

Tell the orchestrator that `/Users/Shared/t009-dry-run.json` exists. A `refused` verdict is not a
failure of the procedure: it names what to fix. Two checks can refuse on this machine for reasons no
command here can fix, and each needs a founder decision plus a code change and a new security re-check:
`os-supported` (the backend accepts the macOS 27.0.x series only, NC-3; this machine runs 27.2) and
`user-is-not-console-user` (the backend refuses the console user, and under fast user switching the
account whose session is in front owns `/dev/console`). Do not continue to step 11 until the
orchestrator confirms in writing that the verdict is `ready` and matches the pins it recomputed.

**Step 11. The real attempt (only after the orchestrator confirms).** Same command without `--dry-run`
and with `--founder-go`. It asks you to type the attempt name, then, before and after each of at most
three sessions, for the Claude Desktop usage card: 5-hour %, weekly %, whether extra usage is on, and
the time you read it (HH:MM). A reading older than five minutes, a missing one, a start at 90 % or more
of the 5-hour window, or a session that used more than 2 points stops the attempt. Where the card is
read (Claude Desktop in your own session, which means switching users, or another surface of the same
account) is a founder decision the driver cannot check. It prints the bundle SHA-256 at the end
whatever the outcome.

```sh
"$BRAID/python312/bin/python3.12" -B -I "$BRAID/repo-$SHORT/scripts/har_t009_attempt.py" \
  <the same arguments as step 10, without --dry-run> --founder-go
cp -R "$HOME/t009/out/t009-20261104" /Users/Shared/t009-bundle-20261104
```

Then, back in your own session, take ownership of the copy (`sudo chown -R "$USER"
/Users/Shared/t009-bundle-20261104`), review the bundle for local identifiers and copy it to
`specs/065-native-claude-containment/evidence/qualification/<attempt>/`.

### Teardown (after the bundle is copied)

```sh
rm -r /Users/Shared/t009-bundle-20261104 /Users/Shared/t009-dry-run.json
# log out of braidlab (Apple menu, Log Out) and revoke its Claude session in the account settings
sudo sysadminctl -deleteUser "$ACCT"           # removes the account, its home and its keychain
ls /Users                                      # braidlab gone (else: sudo rm -r /Users/braidlab)
sudo rm -r "$BRAID"                            # claude copy, interpreter prefix, code copy
chmod 750 "$HOME"                              # the mode you noted in step 6
dscl . -list /Users | grep -c "^$ACCT\$"       # 0
```
