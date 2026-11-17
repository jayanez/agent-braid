<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Release notes for 0.1.0-alpha.9

Release notes for plugin version `0.1.0-alpha.9`, published on 2026-11-16 as pre-release tag
`agent-braid--v0.1.0-alpha.9` (kept outside [Native AI plugins](NATIVE_PLUGINS.md) so frozen SPEC-069
evidence hashes stay valid; see the
[release record](../../specs/066-system-one-shadow/release-acceptance-alpha9.md) and
[`evidence/release-alpha9.json`](../../specs/066-system-one-shadow/evidence/release-alpha9.json)).
Adds no registry migration.

> **Version 0.1.0-alpha.9: System One rule advice, merge-outcome join and automatic
> rollback (SPEC-066), reproducible build.**
>
> - **System One DP-1 structural rule (#1375, #1379).** For a pair that System 2 left
>   `unknown`, a small auditable rule (`dp1-structural-rule-v1`) answers
>   `likely-independent` only when every clause holds and `undetermined` otherwise. It
>   never says `likely-conflicting`, never changes the report or any classification and
>   grants no authority; it is a rule, not a learned model, and its calibration is
>   absent.
> - **`systemOneAdvice` and `advise` consent.** `plugin setup --system-one advise`
>   records the consent; `analyze-work` then adds `systemOneAdvice` beside the report
>   only while advise is effective. Every other state serves `off` or `shadow`.
>   `plugin-status` reports the configured and active mode, the reason and the
>   promotion registry. Shadow episodes keep being recorded under advise.
> - **Owner promotion (`system-one promote`, #1375).** Advise becomes effective for
>   decision point DP-1 only after an owner go pinned to the installed rule manifest:
>   `promote --decision-point DP-1 --go` previews, and `--confirm DIGEST` records it;
>   `--rollback` demotes DP-1 to off.
> - **Merge-outcome join and automatic rollback (#1389).** Merge outcomes of the owner's
>   parallel work are recorded per pair of branch heads and joined to shadow episodes.
>   The first joined merge conflict on a pair advised `likely-independent` rolls DP-1
>   back once, to `shadow` (reason `auto-rollback-false-independence`), so episodes keep
>   being recorded; a later owner go re-enables advise.
> - **Reproducible build, no builder names (#1349).** The source archive has sorted
>   members, commit-time timestamps, uid and gid 0 and no owner names; the wheel is built
>   with `SOURCE_DATE_EPOCH`. Two builds of one commit at different paths are
>   byte-identical, and the local-path guard scans the whole marketplace.
> - **CI shards (#1370).** The complete Python suite runs in six matrix jobs. This does
>   not change the package.
> - **Braid Lightning (experimental, default off).** Further lab work merged since
>   alpha.8 (export CLI with a terms gate, redaction and manifests, SPEC-074/075), plus
>   harness containment and qualification fixes. None of it runs from the MCP server and
>   nothing is promoted without a human decision.
>
> **Limits.**
>
> - **Advise needs an owner go and none exists.** The promotion registry is empty, so
>   `advise` falls back to `shadow` (reason `no-owner-go`) until the owner records a go.
>   Installing alpha.9 does not turn on advice.
> - **Unverified rule.** The DP-1 rule is not calibrated and its advice is labelled
>   `not verified`. Merge outcomes need enough joined pairs before false independence
>   can be bounded; a Wilson bound on few pairs is wide.
> - **Host observation is partial.** The package was built twice byte-identically, verified by
>   `plugin doctor`, compared with a fresh public clone of the tag and installed over alpha.8 in
>   Claude Code. Codex, the OpenCode runtime load, a model-driven smoke on the three hosts and
>   an update on Codex or OpenCode were not observed.
>
> **Rollback.** Reinstall `0.1.0-alpha.8` from tag `agent-braid--v0.1.0-alpha.8`.
> Alpha.8 refuses a registry that records System One `advise` consent: apply
> `plugin setup --system-one shadow` (or `off`) first.
