#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-only
#
# SPEC-065 T009 headless lab launcher (founder decisions of 2026-11-13, evidence/founder-decisions-20261113.json).
#
# Root-owned launcher that starts the T009 driver as the dedicated account in that account's OWN audit session
# without a graphical login: `launchctl asuser <uid>` (launchd manager `Background`). su and sudo from the
# operator's session would keep the operator's audit session and Mach bootstrap namespace (its pasteboard,
# AppleEvents and LaunchServices); the driver and the backend refuse that (`session-own`, `session-not-own`).
#
# It is NOT an authorization and it decides nothing: every check stays in the driver and the backend.
# This repository copy is a template. quickstart.md "Headless own-session mode" installs a copy with the pins
# below filled in, as root:wheel 0755, at /usr/local/libexec/braid/t009-launch.sh. The installed copy reads no
# other file for its configuration (no source, no environment), and refuses to run from any other path.
#
# Usage (as root, through sudo, from any Terminal of the operator):
#   sudo /usr/local/libexec/braid/t009-launch.sh check ATTEMPT   driver --dry-run, then --self-check (no session)
#   sudo /usr/local/libexec/braid/t009-launch.sh diag ATTEMPT    `claude auth status` with the token (no model)
#   sudo /usr/local/libexec/braid/t009-launch.sh run ATTEMPT     the real attempt: at most 3 Haiku sessions; asks
#                                                                 for the attempt name and the usage readings
# check and diag may be allowed without a password by a narrow sudoers rule; run is never in that rule.
# Results are published to /Users/Shared (t009-dry-run.json, t009-self-check.json, t009-diag.txt,
# t009-run-ATTEMPT.txt, t009-bundle-ATTEMPT/) by the lab account, as the graphical lab script does.
# Exit codes: 2 for a refusal of this launcher (STOP line); otherwise the driver's own exit code.
set -u -o pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin
export PATH
umask 077

# --- pins, filled in at install time (quickstart.md); a placeholder left here refuses ---------------------
COMMIT='@COMMIT@'
CLAUDE_SHA256='@CLAUDE_SHA256@'
PYTHON_SHA256='@PYTHON_SHA256@'
SANDBOX_EXEC_SHA256='@SANDBOX_EXEC_SHA256@'
OPERATOR_ACCOUNT='@OPERATOR_ACCOUNT@'

ACCOUNT=braidlab
BRAID=/usr/local/libexec/braid
INSTALLED=$BRAID/t009-launch.sh
LAB_HOME=/Users/$ACCOUNT
SHARED=/Users/Shared

stop() { printf 'STOP: %s\n' "$1" >&2; exit 2; }

valid_mode() { case "$1" in check|diag|run) return 0 ;; *) return 1 ;; esac; }
valid_attempt() { [[ "$1" =~ ^t009-[0-9]{8}[a-z]$ ]]; }

check_pins() {
  [[ "$COMMIT" =~ ^[0-9a-f]{40}$ ]] || stop "pins not installed (COMMIT); install the launcher as quickstart.md says"
  local h
  for h in "$CLAUDE_SHA256" "$PYTHON_SHA256" "$SANDBOX_EXEC_SHA256"; do
    [[ "$h" =~ ^[0-9a-f]{64}$ ]] || stop "pins not installed (a SHA-256); install the launcher as quickstart.md says"
  done
  [[ "$OPERATOR_ACCOUNT" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]] && [ "$OPERATOR_ACCOUNT" != "$ACCOUNT" ] \
    || stop "pins not installed (OPERATOR_ACCOUNT); install the launcher as quickstart.md says"
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

# --- the lab half: runs as the dedicated account inside its own session -----------------------------------
lab() {
  local mode=$1 attempt=$2
  [ "$(id -un)" = "$ACCOUNT" ] && [ "$(id -u)" -ne 0 ] || stop "the lab half runs only as $ACCOUNT"
  cd "$LAB_HOME" || stop "no home for $ACCOUNT"
  local short=${COMMIT:0:7}
  local py=$BRAID/python312/bin/python3.12
  local driver=$BRAID/repo-$short/scripts/har_t009_attempt.py
  local cfg=$LAB_HOME/t009/config
  local claude=$BRAID/claude-2.1.292
  [ -f "$driver" ] || stop "missing $BRAID/repo-$short (step 5 of quickstart.md at this commit)"
  [ -f "$cfg/oauth-token" ] || stop "no token in the lab config directory (step 9b of quickstart.md)"
  local args=(--attempt "$attempt" --operator-account "$OPERATOR_ACCOUNT"
    --claude "$claude" --claude-sha256 "$CLAUDE_SHA256"
    --interpreter "$py" --interpreter-sha256 "$PYTHON_SHA256"
    --interpreter-root "$BRAID/python312" --sandbox-exec-sha256 "$SANDBOX_EXEC_SHA256"
    --config-dir "$cfg" --run-root "$LAB_HOME/t009/run"
    --arena-parent "$LAB_HOME/t009/arena" --out-dir "$LAB_HOME/t009/out/$attempt")
  local run=("$py" -B -I "$driver" "${args[@]}")
  publish() { cp "$1" "$2" && chmod a+r "$2"; }
  case "$mode" in
    check)
      echo "== dry-run ($attempt, $short, headless own session)"
      "${run[@]}" --dry-run > "$LAB_HOME/t009/dry-run.json"; local dry=$?
      publish "$LAB_HOME/t009/dry-run.json" "$SHARED/t009-dry-run.json"
      grep -o '"verdict": "[a-z-]*"' "$LAB_HOME/t009/dry-run.json" | tail -1
      [ "$dry" -eq 0 ] || { echo "== dry-run refused (exit $dry)"; exit "$dry"; }
      echo "== self-check (no session, no quota)"
      "${run[@]}" --self-check --founder-go > "$LAB_HOME/t009/self-check.json"; local sc=$?
      publish "$LAB_HOME/t009/self-check.json" "$SHARED/t009-self-check.json"
      grep -o '"verdict": "[a-z-]*"' "$LAB_HOME/t009/self-check.json" | tail -1
      echo "== done (self-check exit $sc)"; exit "$sc"
      ;;
    diag)
      # outside the sandbox, no model: does `claude auth status` accept the token of the file? exit codes only
      local out=$SHARED/t009-diag.txt tmp
      : > "$out" || stop "cannot write $out"
      tmp=$(mktemp -d "$LAB_HOME/t009/run/diag-XXXXXX") || stop "no temporary directory"
      auth_status "$tmp" "$cfg" "$claude"
      echo "token-env-empty-config exit=$?" | tee -a "$out"
      auth_status "$cfg" "$cfg" "$claude"
      echo "token-env-real-config exit=$?" | tee -a "$out"
      rm -rf "$tmp"; chmod a+r "$out"
      ;;
    run)
      [ -t 0 ] || stop "run needs your terminal: it asks for the attempt name and the usage readings"
      echo "== REAL ATTEMPT $attempt (at most 3 Haiku sessions). Keep claude.ai Usage at hand."
      "${run[@]}" --founder-go 2>&1 | tee "$LAB_HOME/t009/run-$attempt.txt"; local rc=${PIPESTATUS[0]}
      publish "$LAB_HOME/t009/run-$attempt.txt" "$SHARED/t009-run-$attempt.txt"
      if [ -d "$LAB_HOME/t009/out/$attempt" ]; then
        rm -rf "$SHARED/t009-bundle-$attempt"
        cp -R "$LAB_HOME/t009/out/$attempt" "$SHARED/t009-bundle-$attempt"
        chmod -R a+rX "$SHARED/t009-bundle-$attempt"
      fi
      echo "== done (driver exit $rc)"; exit "$rc"
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

[ "$#" -eq 2 ] || stop "usage: t009-launch.sh check|diag|run ATTEMPT"
valid_mode "$1" || stop "mode must be check, diag or run"
valid_attempt "$2" || stop "ATTEMPT must match t009-YYYYMMDDx (one lowercase letter)"
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
echo "== $MODE $ATTEMPT as $ACCOUNT (uid $LAB_UID) in its own session (launchctl asuser)"
# launchctl asuser: a new audit session for the account (auid = its uid) and its own launchd domain;
# sudo -u drops root inside it; env -i: nothing of the caller's environment reaches the lab half.
exec /bin/launchctl asuser "$LAB_UID" /usr/bin/sudo -u "$ACCOUNT" /usr/bin/env -i \
  HOME="$LAB_HOME" USER="$ACCOUNT" LOGNAME="$ACCOUNT" PATH=/usr/bin:/bin LANG=en_US.UTF-8 \
  CLAUDE_CONFIG_DIR="$LAB_HOME/t009/config" DISABLE_AUTOUPDATER=1 \
  /bin/bash "$INSTALLED" __lab "$MODE" "$ATTEMPT"
