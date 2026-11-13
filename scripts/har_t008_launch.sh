#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-only
#
# SPEC-048 T008 headless lab launcher (founder decision T008-7 of 2026-11-13,
# specs/048-harness-variant-laboratory/evidence/founder-decisions-20261113.json).
#
# Root-owned launcher that starts the T008 cohort driver (scripts/har_t008_unit.py) as the dedicated account in
# that account's OWN audit session without a graphical login: `launchctl asuser <uid>` (launchd manager
# `Background`), the session kind the SPEC-065 records of 2026-11-13 are bound to. It mirrors the SPEC-065 T009
# launcher (scripts/har_t009_launch.sh), which stays unchanged because its bytes are bound by SPEC-065 evidence.
#
# It is NOT an authorization and it decides nothing: every check stays in the driver and the backend (window,
# at most 4 units, D2 caps, issued-record expiry, session-own, environment hash, MDRV-04 guard).
# This repository copy is a template. scripts/har_t008_install.sh installs a copy with the pins below filled in,
# as root:wheel 0755, at /usr/local/libexec/braid/t008-launch.sh. The installed copy reads no other file for its
# configuration (no source, no environment), and refuses to run from any other path.
#
# Usage (as root, through sudo, from any Terminal of the operator):
#   sudo /usr/local/libexec/braid/t008-launch.sh check ATTEMPT   driver --dry-run, then `claude auth status` with
#                                                                 the token and an empty config (no model, no quota)
#   sudo /usr/local/libexec/braid/t008-launch.sh run ATTEMPT     the cohort: at most 4 serial Haiku units; asks for
#                                                                 the attempt name and the usage readings
# check may be allowed without a password by a narrow sudoers rule; run is never in that rule.
# One lab step at a time: every mode holds an exclusive lock (lockf(1)) for its whole life on the SAME root-owned
# file as the T009 launcher, so no T008 or T009 step can start beside another one on the shared lab account.
# Results are published by the lab account into its own directory /Users/Shared/braid-t008-lab (dry-run.json,
# auth.txt, run-ATTEMPT.txt): owned by braidlab, mode 755, every file written to a fresh temporary name there and
# renamed into place, so no path another user can plant is ever followed.
# Exit codes: 2 for a refusal of this launcher (STOP line); otherwise the driver's own exit code.
set -u -o pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin
export PATH
umask 077

# --- pins, filled in at install time (scripts/har_t008_install.sh); a placeholder left here refuses ----------
COMMIT='@COMMIT@'
CLAUDE_SHA256='@CLAUDE_SHA256@'
PYTHON_SHA256='@PYTHON_SHA256@'
SANDBOX_EXEC_SHA256='@SANDBOX_EXEC_SHA256@'
OPERATOR_ACCOUNT='@OPERATOR_ACCOUNT@'

ACCOUNT=braidlab
BRAID=/usr/local/libexec/braid
INSTALLED=$BRAID/t008-launch.sh
LAB_HOME=/Users/$ACCOUNT
PUB=/Users/Shared/braid-t008-lab
LOCK=$BRAID/.t009-launch.lock  # shared with t009-launch.sh: one lab step at a time on the lab account

stop() { printf 'STOP: %s\n' "$1" >&2; exit 2; }

valid_mode() { case "$1" in check|run) return 0 ;; *) return 1 ;; esac; }
valid_attempt() { [[ "$1" =~ ^t008-[0-9]{8}[a-z]$ ]]; }

check_pins() {
  [[ "$COMMIT" =~ ^[0-9a-f]{40}$ ]] || stop "pins not installed (COMMIT); install the launcher with har_t008_install.sh"
  local h
  for h in "$CLAUDE_SHA256" "$PYTHON_SHA256" "$SANDBOX_EXEC_SHA256"; do
    [[ "$h" =~ ^[0-9a-f]{64}$ ]] || stop "pins not installed (a SHA-256); install the launcher with har_t008_install.sh"
  done
  [[ "$OPERATOR_ACCOUNT" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]] && [ "$OPERATOR_ACCOUNT" != "$ACCOUNT" ] \
    || stop "pins not installed (OPERATOR_ACCOUNT); install the launcher with har_t008_install.sh"
}

# root-owned, not writable by group or other: the file and every directory above it
root_owned() {
  local path=$1 owner mode
  while :; do
    [ -e "$path" ] && [ ! -L "$path" ] || return 1
    owner=$(stat -f '%u' "$path") && mode=$(stat -f '%Lp' "$path") || return 1
    [ "$owner" = 0 ] && (( (8#$mode & 8#022) == 0 )) || return 1
    [ "$path" = / ] && return 0
    path=$(dirname "$path")
  done
}

# `claude auth status` with config dir $1 and the token of $2/oauth-token. The token is read and exported by bash
# builtins only, so it never appears in a process's arguments; only the exit code is kept.
auth_status() {
  (
    for name in $(compgen -e); do unset "$name"; done
    export HOME=$LAB_HOME PATH=/usr/bin:/bin CLAUDE_CONFIG_DIR=$1 DISABLE_AUTOUPDATER=1
    CLAUDE_CODE_OAUTH_TOKEN=$(< "$2/oauth-token") || exit 1
    export CLAUDE_CODE_OAUTH_TOKEN
    exec "$3" auth status
  ) >/dev/null 2>&1
}

# The publish directory: a real directory (no symlink) owned by the running account, not writable by group or
# other. Created when missing. /Users/Shared is sticky, so nobody else can rename or replace it once it is ours.
prepare_pub() {
  if [ ! -e "$PUB" ] && [ ! -L "$PUB" ]; then
    mkdir -m 755 "$PUB" || stop "cannot create $PUB"
  fi
  [ -d "$PUB" ] && [ ! -L "$PUB" ] || stop "$PUB is not a real directory (remove it and run again)"
  local owner mode
  owner=$(stat -f '%u' "$PUB") && mode=$(stat -f '%Lp' "$PUB") || stop "cannot inspect $PUB"
  [ "$owner" = "$(id -u)" ] && (( (8#$mode & 8#022) == 0 )) \
    || stop "$PUB is not owned by $(id -un) or is writable by others (remove it and run again)"
}

# Copy file $1 to $PUB/$2 (mode 644): written to a fresh mktemp name in $PUB, then renamed into place. A target
# that exists as anything but a regular file (a symlink, a directory) refuses.
publish() {
  local name=$PUB/$2 tmp
  if [ -L "$name" ] || { [ -e "$name" ] && [ ! -f "$name" ]; }; then stop "$name is not a regular file"; fi
  tmp=$(mktemp "$PUB/.publish-XXXXXX") || stop "cannot publish $2"
  if cat "$1" > "$tmp" && chmod 644 "$tmp" && mv -f "$tmp" "$name"; then return 0; fi
  rm -f "$tmp"; stop "cannot publish $2"
}

# Refuse to publish file $1 (world-readable in $PUB) if it holds the token of file $2 or an Anthropic key prefix.
no_token() {
  local tok=""
  IFS= read -r tok < "$2" || [ -n "$tok" ] || stop "cannot read the token to screen $1"
  if { [ "${#tok}" -ge 16 ] && grep -qF -- "$tok" "$1"; } || grep -q 'sk-ant-' "$1"; then
    stop "$1 holds a credential; not published (kept only in the lab account's home)"
  fi
}

# --- the lab half: runs as the dedicated account inside its own session -----------------------------------
lab() {
  local mode=$1 attempt=$2
  [ "$(id -un)" = "$ACCOUNT" ] && [ "$(id -u)" -ne 0 ] || stop "the lab half runs only as $ACCOUNT"
  cd "$LAB_HOME" || stop "no home for $ACCOUNT"
  local short=${COMMIT:0:7}
  local py=$BRAID/python312/bin/python3.12
  local driver=$BRAID/repo-$short/scripts/har_t008_unit.py
  local cfg=$LAB_HOME/t009/config  # the SPEC-065 lab state (login, token, run and arena roots) is reused as is
  local claude=$BRAID/claude-2.1.292
  local work=$LAB_HOME/t008
  [ -f "$driver" ] || stop "missing $driver (install the code copy with har_t008_install.sh)"
  root_owned "$driver" || stop "$driver or a directory above it is not root-owned or is writable by others"
  [ -f "$cfg/oauth-token" ] || stop "no token in the lab config directory (SPEC-065 quickstart step 9b)"
  mkdir -p "$work/out" && chmod 700 "$work" "$work/out" || stop "cannot create $work/out"
  local args=(--attempt "$attempt" --operator-account "$OPERATOR_ACCOUNT"
    --claude "$claude" --claude-sha256 "$CLAUDE_SHA256"
    --interpreter "$py" --interpreter-sha256 "$PYTHON_SHA256"
    --interpreter-root "$BRAID/python312" --sandbox-exec-sha256 "$SANDBOX_EXEC_SHA256"
    --config-dir "$cfg" --run-root "$LAB_HOME/t009/run"
    --arena-parent "$LAB_HOME/t009/arena" --out-dir "$work/out/$attempt")
  local run=("$py" -B -I -u "$driver" "${args[@]}")
  prepare_pub
  case "$mode" in
    check)
      echo "== dry-run ($attempt, $short, headless own session)"
      "${run[@]}" --dry-run > "$work/dry-run.json"; local dry=$?
      no_token "$work/dry-run.json" "$cfg/oauth-token"
      publish "$work/dry-run.json" dry-run.json
      grep -o '"verdict": "[a-z-]*"' "$work/dry-run.json" | tail -1
      [ "$dry" -eq 0 ] || { echo "== dry-run refused (exit $dry)"; exit "$dry"; }
      # outside the sandbox, no model: does `claude auth status` accept the token of the file? exit code only;
      # an empty temporary config directory, so the lab's real config directory is not touched
      echo "== auth status (token, empty config; no model, no quota)"
      local out tmp
      out=$(mktemp "$work/auth-XXXXXX") || stop "no temporary file"
      tmp=$(mktemp -d "$work/auth-XXXXXX") || stop "no temporary directory"
      auth_status "$tmp" "$cfg" "$claude"; local auth=$?
      rm -rf "$tmp"
      echo "token-env-empty-config exit=$auth" | tee "$out"
      publish "$out" auth.txt; rm -f "$out"
      echo "== done (auth status exit $auth)"; exit "$auth"
      ;;
    run)
      [ -t 0 ] || stop "run needs your terminal: it asks for the attempt name and the usage readings"
      [ ! -e "$work/run-$attempt.txt" ] && [ ! -L "$work/run-$attempt.txt" ] \
        || stop "attempt $attempt already ran (its transcript is kept); the orchestrator names a new label"
      echo "== T008 COHORT $attempt (at most 4 serial Haiku units). Keep claude.ai Usage at hand."
      # Ctrl-C reaches the driver, which prints its aborted report (evidence). tee ignores it, so the transcript
      # keeps that report; this shell only notes it (a handler, not an ignore: the driver keeps its default) and
      # publishes the transcript whatever happened.
      trap ':' INT
      "${run[@]}" --founder-go 2>&1 | (trap '' INT; exec tee "$work/run-$attempt.txt"); local rc=${PIPESTATUS[0]}
      no_token "$work/run-$attempt.txt" "$cfg/oauth-token"
      publish "$work/run-$attempt.txt" "run-$attempt.txt"
      echo "== done (driver exit $rc; the transcript ends with the driver's JSON report)"; exit "$rc"
      ;;
  esac
}

# --- entry -------------------------------------------------------------------------------------------------
if [ "${1:-}" = "__lab" ]; then
  [ "$#" -eq 3 ] && valid_mode "$2" && valid_attempt "$3" || stop "internal entry misused"
  check_pins
  lab "$2" "$3"
  exit 0
fi

[ "$#" -eq 2 ] || stop "usage: t008-launch.sh check|run ATTEMPT"
valid_mode "$1" || stop "mode must be check or run"
valid_attempt "$2" || stop "ATTEMPT must match t008-YYYYMMDDx (one lowercase letter)"
MODE=$1
ATTEMPT=$2
check_pins
[ "$(id -u)" -eq 0 ] || stop "run it with sudo (it starts the lab account's own session as root)"
[ "$0" = "$INSTALLED" ] || stop "run the installed copy $INSTALLED, not $0"
root_owned "$INSTALLED" || stop "$INSTALLED or a directory above it is not root-owned or is writable by others"
LAB_UID=$(id -u "$ACCOUNT" 2>/dev/null) || stop "no account $ACCOUNT"
OPERATOR_UID=$(id -u "$OPERATOR_ACCOUNT" 2>/dev/null) || stop "no account $OPERATOR_ACCOUNT"
[[ "$LAB_UID" =~ ^[0-9]+$ ]] && [ "$LAB_UID" -ge 500 ] && [ "$LAB_UID" -ne "$OPERATOR_UID" ] \
  || stop "$ACCOUNT must be a human account (uid >= 500) other than $OPERATOR_ACCOUNT"
cd / || stop "cannot leave the caller's directory"
# One lab step at a time, as in t009-launch.sh: the first call only tests (-t 0: never wait) so the refusal has a
# clear line; the second holds the kernel lock for the whole step and the kernel drops it when lockf exits.
# Residual shared with t009-launch.sh: a SIGTERM sent by root to lockf itself frees the lock while the step goes on.
if [ -L "$LOCK" ] || { [ -e "$LOCK" ] && [ ! -f "$LOCK" ]; }; then stop "$LOCK is not a regular file"; fi
/usr/bin/lockf -k -s -t 0 "$LOCK" /usr/bin/true || stop "another lab step is running (T008 or T009)"
echo "== $MODE $ATTEMPT as $ACCOUNT (uid $LAB_UID) in its own session (launchctl asuser)"
# launchctl asuser: a new audit session for the account (auid = its uid) and its own launchd domain;
# sudo -u drops root inside it (and closes every descriptor above 2); env -i: nothing of the caller's
# environment reaches the lab half.
exec /usr/bin/lockf -k -t 0 "$LOCK" /bin/launchctl asuser "$LAB_UID" /usr/bin/sudo -u "$ACCOUNT" /usr/bin/env -i \
  HOME="$LAB_HOME" USER="$ACCOUNT" LOGNAME="$ACCOUNT" PATH=/usr/bin:/bin LANG=en_US.UTF-8 \
  CLAUDE_CONFIG_DIR="$LAB_HOME/t009/config" DISABLE_AUTOUPDATER=1 \
  /bin/bash "$INSTALLED" __lab "$MODE" "$ATTEMPT"
