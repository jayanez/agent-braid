#!/bin/sh
# SPDX-License-Identifier: AGPL-3.0-only
# Alternative frontend to the native plugin managers; no Python bootstrap.
set -eu
plugin_host=auto
plugin_marketplace=https://github.com/jayanez/agent-braid.git
plugin_ref=plugin-dist
plugin_ref_explicit=false
plugin_dry_run=false
usage() {
    printf '%s\n' 'Usage: sh install.sh [--host codex|claude|both] [--marketplace URL_OR_PATH] [--ref REF] [--dry-run]'
}
refuse() { printf 'Agent Braid installer: %s\n' "$*" >&2; exit 2; }
while [ "$#" -gt 0 ]; do
    case "$1" in
        --host|--marketplace|--ref)
            [ "$#" -ge 2 ] || refuse "Missing value for $1"
            case "$2" in ''|-*) refuse "Invalid value for $1" ;; esac
            case "$1" in
                --host) plugin_host=$2 ;;
                --marketplace) plugin_marketplace=$2; [ "$plugin_ref_explicit" = true ] || plugin_ref= ;;
                --ref) plugin_ref=$2; plugin_ref_explicit=true ;;
            esac
            shift 2 ;;
        --dry-run) plugin_dry_run=true; shift ;;
        --help|-h) usage; exit 0 ;;
        *) usage >&2; refuse "Unknown option: $1" ;;
    esac
done
case "$plugin_host" in auto|codex|claude|both) ;; *) refuse 'Select codex, claude or both' ;; esac
[ -n "$plugin_marketplace" ] || refuse 'Marketplace cannot be empty'
command -v git >/dev/null 2>&1 || refuse 'Git is required by the native marketplace managers'
plugin_codex=false
plugin_claude=false
command -v codex >/dev/null 2>&1 && plugin_codex=true
command -v claude >/dev/null 2>&1 && plugin_claude=true
if [ "$plugin_host" = auto ]; then
    if [ "$plugin_codex:$plugin_claude" = true:true ]; then
        if [ -t 0 ]; then
            printf 'Install for codex, claude or both? ' >&2
            read -r plugin_host
            case "$plugin_host" in codex|claude|both) ;; *) refuse 'No valid host selected' ;; esac
        else
            refuse 'Both hosts found; pass --host codex, --host claude or --host both'
        fi
    elif [ "$plugin_codex" = true ]; then plugin_host=codex
    elif [ "$plugin_claude" = true ]; then plugin_host=claude
    else refuse 'Install Codex or Claude Code first, then rerun this command'
    fi
fi
# Preflight every selected host before changing either one.
case "$plugin_host" in codex|both) [ "$plugin_codex" = true ] || refuse 'Codex is unavailable' ;; esac
case "$plugin_host" in claude|both) [ "$plugin_claude" = true ] || refuse 'Claude Code is unavailable' ;; esac
run() {
    if [ "$plugin_dry_run" = true ]; then
        printf 'Would run:'
        printf ' <%s>' "$@"
        printf '\n'
    else
        "$@" || refuse 'Native manager failed; inspect its output. Earlier selected host operations may already have completed.'
    fi
}
case "$plugin_host" in
    codex|both)
        if [ -n "$plugin_ref" ]; then
            run codex plugin marketplace add "$plugin_marketplace" --ref "$plugin_ref"
        else
            run codex plugin marketplace add "$plugin_marketplace"
        fi
        run codex plugin add agent-braid@agent-braid ;;
esac
case "$plugin_host" in
    claude|both)
        plugin_claude_source=$plugin_marketplace
        [ -z "$plugin_ref" ] || plugin_claude_source="$plugin_marketplace#$plugin_ref"
        run claude plugin install agent-braid --marketplace "$plugin_claude_source" --scope user ;;
esac
printf '%s\n' 'Next: open Agent Braid setup in your selected local host, select repositories, inspect/apply the preview and reconnect MCP.'
printf '%s\n' 'No provider session was started. Native managers own plugin updates and removal.'
