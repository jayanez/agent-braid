<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Native plugin submission preparation

Status: prepared source material; no submission or public release is claimed.
Owner approval to publish and provider eligibility/review are external gates.
The Git marketplace provides the full bundled-runtime experience independently
of either directory's acceptance. The package cannot be replaced with an installer
that requires Python, uv, Node or Docker to bypass a directory restriction.

## Shared listing material

- Name/slug: Agent Braid / `agent-braid`.
- Developer: Juan Antonio Yáñez García (`jayanez` on GitHub).
- Summary: Inspect agent interactions with evidence and explicit workspace boundaries.
- Description: Analyze declared agent work, inspect conservative conflicts and
  replay evidence, and use explicitly authorized local Git operations. Select
  repositories through setup and retain separate private results for each.
- Category: Developer Tools. Initial targets: local Codex and Claude Code,
  macOS arm64 and Linux x86_64; no browser/cloud host or Windows compatibility claim.
- Source/support: https://github.com/jayanez/agent-braid and its issue tracker.
- Privacy: [policy](../PLUGIN_PRIVACY.md).
- Terms/licenses: repository LICENSE, NOTICE, LICENSES and runtime/dependency
  metadata in the candidate's `provenance.json`.
- Icon: `integrations/agent-braid/plugin/icon.svg`, packaged as `assets/icon.svg`.
- Installation/setup/lifecycle: [guide](../NATIVE_PLUGINS.md).
- Permissions: local stdio, explicitly registered source roots, private workspace
  results, Git for Git operations; no service credentials, network telemetry or
  automatic execution authorization.

## Optional workflow component (unreleased)

The listing material above describes the five product skills plus setup, which
are unchanged. An optional, Claude-only `braid-gate` workflow
([SPEC-052](../../../specs/052-claude-workflow-gate/spec.md),
[recipe](../CLAUDE_WORKFLOWS.md)) is specified but unreleased and is not part of
any submitted candidate. Codex is expected to ignore it (not observed). By design
it makes no network access, no source-state writes (only a temporary scratch
directory) and no grants, which depends on an unverified host allowlist. Do not list or describe it in any submission, and
do not claim compatibility for any host, until the ADR 0024 amendment is adopted
and host behaviors are observed on a recorded Claude Code version.

## Reviewer test cases

1. Install the clean source-bound marketplace in a fresh user profile; verify six
   discovered skill files (five product plus setup), metadata and stdio configuration.
2. Run bundled doctor with external Python/package managers absent from PATH;
   verify inventory, runtime and Git. Relocate to a path with spaces and repeat.
3. Invoke setup with no configuration. Suggest current/registered repositories;
   scan only a selected folder. Cancel and confirm no registry was written.
4. Select two repositories, preview once, apply the digest, reconnect. Analyze a
   harmless AIM fixture for each explicit workspaceId. Compare core result values.
5. Refuse unknown workspace IDs, arbitrary roots, cross-workspace resource URIs,
   execution without runtime opt-in, and stale bindings after a registry change.
6. Apply a stale preview and confirm no configuration change. Unregister and
   confirm source/results survive. Migrate a receipt with an edited skill and
   confirm residuals are retained.
7. Update/reinstall/remove using the native manager. Confirm private application
   state survives. Record exact native versions and separate protocol observations
   from actual interactive host behavior.

Automated controls live in `tests/test_plugin_*.py`; clean package/native
procedures and their limits belong to SPEC-046. Never submit fabricated screenshots,
ratings or interaction evidence. Add actual sanitized interactive screenshots only
when obtained with the final candidate.

## OpenAI route — T011

The portable root manifest contains `extensions.com.openai` with local execution,
setup onboarding, support/privacy/license links and branding. Root skills and
`mcp.json` are generated alongside the Claude files from the same sources.

[Local stdio publishing](https://developers.openai.com/plugins/deploy/desktop-only)
requires approved-partner eligibility/organization allowlisting. Eligibility has
not been established for this owner. [Submission](https://developers.openai.com/plugins/deploy/submission)
also requires an eligible verified identity and the current review process.
Before submission: verify partner access in the owner's account, freeze a clean
versioned distribution, obtain actual host acceptance/screenshots, confirm required
image formats and public URLs against the then-current portal, and obtain founder
publication approval. Do not claim that local native installation grants eligibility.

External state: **blocked on owner eligibility confirmation and publication
approval**. No partner application/contact or provider submission was sent.

## Anthropic routes — T012

The native package includes `.claude-plugin/plugin.json`, `.mcp.json`, skills and
the owner marketplace catalog. Native Claude validation and user install are
separate from directory acceptance.

[Directory publishing](https://code.claude.com/docs/en/plugins/publish) uses
`claude.ai/directory/manage`, an eligible paid plan and an authorized GitHub
connection with repository write access. The repository must be public by actual
publication. Inclusion in `anthropics/claude-plugins-official` follows its separate
partner/contact route; directory submission does not imply that inclusion.

The [pre-submission checklist](https://claude.com/docs/plugins/pre-submission-checklist)
sets a repository archive limit of 50 MiB, unpacked limit of 256 MiB and a hard
per-file limit of 5 MiB. Executables, files above 256 KiB and more than 512 files
also require review. The bundled CPython candidate contains thousands of files and
executables larger than 5 MiB. Its two-platform archive/unpacked sizes and largest
files must be recorded from the final inventory before submission. Bundling both
platforms is expected to exceed ordinary directory limits; approval or a supported
alternative distribution arrangement is required. LFS/pointer files and symlinks
cannot be used to evade these restrictions.

The [platform support rules](https://claude.com/docs/plugins/platform-support)
also constrain executable plugins in chat/Cowork; this candidate targets local
Claude Code only. The bundle is not advertised as chat/Cowork compatible.

External state: **blocked on executable/size distribution review, account access
and founder publication approval**. The material above is ready for owner review;
portal submission and direct official-marketplace contact have not been sent.
