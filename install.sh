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
    printf '%s\n' 'Usage: sh install.sh [--host codex|claude|opencode|all] [--marketplace URL_OR_PATH] [--ref REF] [--dry-run]'
    printf '%s\n' '  all installs for every supported host found on PATH (Codex, Claude Code, OpenCode); both is a deprecated alias for codex + claude only.'
}
skip() { printf 'Agent Braid installer: %s not found on PATH; skipping.\n' "$1" >&2; }
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
case "$plugin_host" in auto|codex|claude|opencode|all|both) ;; *) refuse 'Select codex, claude, opencode or all' ;; esac
[ -n "$plugin_marketplace" ] || refuse 'Marketplace cannot be empty'
command -v git >/dev/null 2>&1 || refuse 'Git is required by the native marketplace managers'
plugin_codex=false
plugin_claude=false
plugin_opencode=false
command -v codex >/dev/null 2>&1 && plugin_codex=true
command -v claude >/dev/null 2>&1 && plugin_claude=true
command -v opencode >/dev/null 2>&1 && plugin_opencode=true
if [ "$plugin_host" = auto ]; then
    if [ "$plugin_codex:$plugin_claude" = true:true ]; then
        if [ -t 0 ]; then
            printf 'Install for codex, claude or all? ' >&2
            read -r plugin_host
            case "$plugin_host" in codex|claude|all) ;; *) refuse 'No valid host selected' ;; esac
        else
            refuse 'Both hosts found; pass --host codex, --host claude or --host all'
        fi
    elif [ "$plugin_codex" = true ]; then plugin_host=codex
    elif [ "$plugin_claude" = true ]; then plugin_host=claude
    elif [ "$plugin_opencode" = true ]; then plugin_host=opencode
    else refuse 'Install Codex, Claude Code or OpenCode first, then rerun this command'
    fi
fi
# Resolve the selected hosts and preflight them all before changing any.
plugin_do_codex=false
plugin_do_claude=false
plugin_do_opencode=false
case "$plugin_host" in
    codex) plugin_do_codex=true ;;
    claude) plugin_do_claude=true ;;
    opencode) plugin_do_opencode=true ;;
    both)
        printf '%s\n' 'Agent Braid installer: --host both is deprecated; use --host all.' >&2
        plugin_do_codex=true
        plugin_do_claude=true ;;
    all)
        if [ "$plugin_codex" = true ]; then plugin_do_codex=true; else skip Codex; fi
        if [ "$plugin_claude" = true ]; then plugin_do_claude=true; else skip 'Claude Code'; fi
        if [ "$plugin_opencode" = true ]; then plugin_do_opencode=true; else skip OpenCode; fi
        [ "$plugin_do_codex:$plugin_do_claude:$plugin_do_opencode" != false:false:false ] || refuse 'No supported host found; install Codex, Claude Code or OpenCode first, then rerun this command' ;;
esac
[ "$plugin_do_codex" = false ] || [ "$plugin_codex" = true ] || refuse 'Codex is unavailable'
[ "$plugin_do_claude" = false ] || [ "$plugin_claude" = true ] || refuse 'Claude Code is unavailable'
[ "$plugin_do_opencode" = false ] || [ "$plugin_opencode" = true ] || refuse 'OpenCode is unavailable'
run() {
    if [ "$plugin_dry_run" = true ]; then
        printf 'Would run:'
        printf ' <%s>' "$@"
        printf '\n'
    else
        "$@" || refuse 'Native manager failed; inspect its output. Earlier selected host operations may already have completed.'
    fi
}
if [ "$plugin_do_codex" = true ]; then
    if [ -n "$plugin_ref" ]; then
        run codex plugin marketplace add "$plugin_marketplace" --ref "$plugin_ref"
    else
        run codex plugin marketplace add "$plugin_marketplace"
    fi
    run codex plugin add agent-braid@agent-braid
fi
if [ "$plugin_do_claude" = true ]; then
    plugin_claude_source=$plugin_marketplace
    [ -z "$plugin_ref" ] || plugin_claude_source="$plugin_marketplace#$plugin_ref"
    run claude plugin install agent-braid --marketplace "$plugin_claude_source" --scope user
fi
if [ "$plugin_do_opencode" = true ]; then
    # OpenCode installs from a Git source, not a marketplace: map the marketplace to one.
    case "$plugin_marketplace" in
        https://github.com/*/*) plugin_opencode_source=${plugin_marketplace#https://github.com/}
            plugin_opencode_source=github:${plugin_opencode_source%.git} ;;
        /*) plugin_opencode_source=git+file://$plugin_marketplace ;;
        *) plugin_opencode_source=git+$plugin_marketplace ;;
    esac
    [ -z "$plugin_ref" ] || plugin_opencode_source="$plugin_opencode_source#$plugin_ref"
    run opencode plugin add "$plugin_opencode_source::path:plugins/agent-braid"
fi
printf '%s\n' 'Next: open Agent Braid setup in your selected local host, select repositories, inspect/apply the preview and reconnect MCP.'
printf '%s\n' 'No provider session was started. Native managers own plugin updates and removal.'
