#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-only
#
# SPEC-048 T008 headless install (founder decision T008-7 of 2026-11-13): the owner's one command that prepares
# the root launcher of scripts/har_t008_launch.sh. It is NOT an authorization and runs nothing native (no claude,
# no sandbox-exec, no launchctl); it only fetches, copies, renders and checks files, with sudo where root is needed.
#
# This repository copy is a template. The orchestrator renders it with the same pins as the launcher (the merged
# commit to install and the SPEC-065 setup pins) by the sed pipeline of the T008 owner packet, writes the rendered
# copy into the owner's home and states its SHA-256. The owner checks that SHA-256 and runs, in Terminal.app, as
# themselves (sudo asks for the password):
#
#   bash ~/t008-install.sh
#
# The code is fetched by commit from the public repository into a fresh temporary repository (no local checkout,
# no user git configuration, no replace refs or attributes), so the copy is exactly the commit's tracked files.
# Steps, each a hard stop (a `STOP:` line, exit 1); every pin and precondition is checked before the first sudo,
# and nothing in /usr/local/libexec/braid or /etc/sudoers.d changes before the code copy is complete:
#   1. a root-owned code copy of COMMIT, staged under a temporary name;
#   2. under the lab lock (no T008 or T009 step can start meanwhile): the copy renamed to
#      /usr/local/libexec/braid/repo-<short> and the launcher rendered from it with the pins, installed root:wheel
#      0755 as /usr/local/libexec/braid/t008-launch.sh;
#   3. the sudoers rule /etc/sudoers.d/braid-t008: the owner may run only `t008-launch.sh check` as root without a
#      password; `run` always asks for it. The SPEC-065 rule /etc/sudoers.d/braid-t009 is left as it is.
# It prints the SHA-256 of the installed launcher, to compare with the copy the orchestrator renders. A STOP after
# a step leaves the earlier steps done; fix the cause and run it again.
# Undo: sudo rm -f /etc/sudoers.d/braid-t008 /usr/local/libexec/braid/t008-launch.sh; sudo rm -r <the code copy>.
set -euo pipefail
stop() { printf 'STOP: %s\n' "$1" >&2; exit 1; }
trap 'stop "a command failed at line $LINENO of the installer"' ERR

# --- pins, filled in by the orchestrator's rendering; a placeholder left here refuses ----------------------
COMMIT='@COMMIT@'
CLAUDE_SHA256='@CLAUDE_SHA256@'
PYTHON_SHA256='@PYTHON_SHA256@'
SANDBOX_EXEC_SHA256='@SANDBOX_EXEC_SHA256@'
OPERATOR_ACCOUNT='@OPERATOR_ACCOUNT@'

REPOSITORY=https://github.com/jayanez/agent-braid.git
B=/usr/local/libexec/braid
LAUNCHER=$B/t008-launch.sh
RULE=/etc/sudoers.d/braid-t008
LOCK=$B/.t009-launch.lock  # the lock both lab launchers hold for a whole step

[[ "$COMMIT" =~ ^[0-9a-f]{40}$ ]] || stop "COMMIT is not rendered (40 hex); ask the orchestrator for the rendered copy"
for h in "$CLAUDE_SHA256" "$PYTHON_SHA256" "$SANDBOX_EXEC_SHA256"; do
  [[ "$h" =~ ^[0-9a-f]{64}$ ]] || stop "a SHA-256 pin is not rendered; ask the orchestrator for the rendered copy"
done
[[ "$OPERATOR_ACCOUNT" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]] && [ "$OPERATOR_ACCOUNT" != braidlab ] \
  || stop "OPERATOR_ACCOUNT is not rendered; ask the orchestrator for the rendered copy"
[ "$(id -u)" -ne 0 ] || stop "run it as yourself, not as root (it uses sudo for each step)"
[ "$(id -un)" = "$OPERATOR_ACCOUNT" ] || stop "rendered for $OPERATOR_ACCOUNT, but you are $(id -un)"
[ "$#" -eq 0 ] || stop "usage: bash t008-install.sh (no arguments)"
SHORT=${COMMIT:0:7}
COPY=$B/repo-$SHORT
STAGE=$B/.stage-$SHORT

# the SPEC-065 lab is still the one the pins name (read-only hashes; the driver checks them again in the lab)
sha() { if [ -f "$1" ] && [ ! -L "$1" ]; then shasum -a 256 "$1" | cut -c1-64; fi; }
[ "$(sha "$B/claude-2.1.292")" = "$CLAUDE_SHA256" ] || stop "$B/claude-2.1.292 does not match its pin"
[ "$(sha "$B/python312/bin/python3.12")" = "$PYTHON_SHA256" ] \
  || stop "$B/python312/bin/python3.12 does not match its pin"
[ "$(sha /usr/bin/sandbox-exec)" = "$SANDBOX_EXEC_SHA256" ] || stop "/usr/bin/sandbox-exec does not match its pin"
# a passwordless root rule may only name a file nobody but root can replace: $B and every directory above it
for d in "$B" /usr/local/libexec /usr/local /usr /; do
  [ -d "$d" ] && [ ! -L "$d" ] && [ "$(stat -f '%u' "$d")" = 0 ] && (( (8#$(stat -f '%Lp' "$d") & 8#022) == 0 )) \
    || stop "$d is not a root-owned directory closed to others"
done
if [ -L "$LOCK" ] || { [ -e "$LOCK" ] && [ ! -f "$LOCK" ]; }; then stop "$LOCK is not a regular file"; fi

echo "== fetching $COMMIT from $REPOSITORY (a fresh temporary repository; your git configuration is not used)"
FETCHED=$(mktemp -d "${TMPDIR:-/tmp}/t008-install-XXXXXX")
cleanup() { rm -rf "$FETCHED"; }
trap cleanup EXIT
fresh_git() { GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_NO_REPLACE_OBJECTS=1 git -C "$FETCHED/repo" "$@"; }
GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null git init -q --bare "$FETCHED/repo"
fresh_git fetch -q --depth 1 "$REPOSITORY" "$COMMIT" || stop "cannot fetch $COMMIT (network, or not merged yet)"
[ "$(fresh_git rev-parse "$COMMIT^{commit}")" = "$COMMIT" ] || stop "the fetched object is not $COMMIT"
fresh_git cat-file -e "$COMMIT:scripts/har_t008_launch.sh" 2>/dev/null || stop "$COMMIT has no har_t008_launch.sh"
fresh_git archive --prefix="repo-$SHORT/" -o "$FETCHED/code.tar" "$COMMIT"

echo "== 1. the code copy, staged as $STAGE (your sudo password)"
sudo grep -qE '^[#@]includedir /(private/)?etc/sudoers.d' /etc/sudoers || stop "no sudoers.d in /etc/sudoers"
sudo rm -rf "$STAGE"
sudo mkdir -m 700 "$STAGE"
sudo tar -x -C "$STAGE" --no-same-owner -f "$FETCHED/code.tar"
sudo chown -R root:wheel "$STAGE/repo-$SHORT"
sudo chmod -R go-w,a+rX "$STAGE/repo-$SHORT"
# [@] keeps these patterns from being placeholders themselves when this template is rendered
sed -e "s/[@]COMMIT[@]/$COMMIT/" -e "s/[@]CLAUDE_SHA256[@]/$CLAUDE_SHA256/" -e "s/[@]PYTHON_SHA256[@]/$PYTHON_SHA256/" \
    -e "s/[@]SANDBOX_EXEC_SHA256[@]/$SANDBOX_EXEC_SHA256/" -e "s/[@]OPERATOR_ACCOUNT[@]/$OPERATOR_ACCOUNT/" \
    "$STAGE/repo-$SHORT/scripts/har_t008_launch.sh" | sudo tee "$STAGE/t008-launch.sh" > /dev/null
if sudo grep -q '[@][A-Z0-9_]*[@]' "$STAGE/t008-launch.sh"; then stop "a pin is not filled in"; fi
sudo chown root:wheel "$STAGE/t008-launch.sh"
sudo chmod 755 "$STAGE/t008-launch.sh"

echo "== 2. under the lab lock: $COPY and $LAUNCHER"
# shellcheck disable=SC2016  # expanded by the root shell, from its arguments
SWAP='set -e; rm -rf "$2"; mv "$1/repo-$4" "$2"; mv -f "$1/t008-launch.sh" "$3"; rmdir "$1"'
sudo /usr/bin/lockf -k -t 0 "$LOCK" /bin/sh -c "$SWAP" sh "$STAGE" "$COPY" "$LAUNCHER" "$SHORT" \
  || stop "a T008 or T009 lab step is running (nothing was replaced), or a move failed; run this again"

echo "== 3. the sudoers rule $RULE: only 'check' without a password"
printf '%s ALL=(root) NOPASSWD: %s\n' "$OPERATOR_ACCOUNT" "$LAUNCHER check *" | sudo tee "$RULE.new" > /dev/null
sudo chmod 440 "$RULE.new"
sudo visudo -cf "$RULE.new" > /dev/null || { sudo rm -f "$RULE.new"; stop "rule invalid"; }
sudo mv -f "$RULE.new" "$RULE"

ls -l "$LAUNCHER"                                 # -rwxr-xr-x  root  wheel
sudo -l | grep -E 't00[89]-launch' || true        # t008 check, plus the t009 check and diag if installed
echo "== send these lines to the orchestrator:"
echo "commit $COMMIT"
shasum -a 256 "$LAUNCHER"
