<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Agent Braid plugin privacy and support

Agent Braid's native plugin runs a local stdio MCP process. It has no hosted
Agent Braid service, analytics, advertising, account or credential collection.
Optional local technical telemetry ([TELEMETRY.md](TELEMETRY.md)) is off by
default, records only daily numeric aggregates on this machine after explicit
consent and is never sent anywhere automatically. Optional System One shadow mode
([SYSTEM_ONE_SHADOW.md](SYSTEM_ONE_SHADOW.md)) is also off by default and needs its
own explicit consent; telemetry consent never implies it. It records only
structural features and salted pseudonyms in a private local store, never names,
paths, prompts or content, and uploads nothing. The plugin does not install or invoke a model provider. Its host's
privacy policy and permissions continue to govern data the host supplies to a
model or other tools.

The user explicitly selects repository roots. Discovery inspects Git metadata
only in the current repository, registered repositories and project folders the
user selects, with depth and entry bounds and no traversal through symlinks.
Selection is not an execution grant. Analysis inputs and local evidence may
contain sensitive paths or content; review host tool inputs and exports before
sharing them.

Workspace configuration and results reside in private user storage, separate
from installed plugin files and repositories. `AGENT_BRAID_HOME` can select an
alternative private location. Registration is previewed before application.
Unregistering a workspace and uninstalling the plugin retain its results. Users
can inspect and remove their own retained application data after preserving any
needed evidence. No deletion request to a remote Agent Braid service is needed.

An optional, Claude-only `braid-gate` workflow is specified but unreleased
([recipe](CLAUDE_WORKFLOWS.md)); Codex ignores it and the product skills and setup
skill are unchanged. If present, its agents read the committed file contents and
diffs of the pinned commits in a registered repository: the Git `merge-tree`
baseline reads the committed trees and blobs, and the plugin's analyzer
(`analyze-work`) reads file effects. They also read the workspace registry rows,
so the registered local source and result paths appear in agent prompts and
results. The gate itself uploads nothing and is designed to contact no network
service, write no source state (its only write is a temporary scratch directory)
and issue no grant; that is intended behavior and depends on the host permission
allowlist, which is unverified on any host. The agents run on the host's model
provider, which therefore receives those prompts and tool results under the
host's own terms. Review the resulting envelope before sharing it.

Runtime execution remains explicitly opt-in and requires existing operator grants;
the plugin neither creates grants nor widens filesystem trust. Reconnection is
required after workspace configuration changes. MCP resources have workspace
ownership boundaries. These controls do not change the host's own permissions.

Support and reproducible bug reports: https://github.com/jayanez/agent-braid/issues
Do not post private repository contents, grants, credentials or complete local
evidence in public issues. Provide host version, platform, candidate/source digest,
sanitized doctor output and the smallest non-sensitive reproduction instead.
Security reports should avoid publishing an exploitable issue or sensitive data;
use any private reporting route enabled on the repository, or contact the owner
through their verified GitHub profile to establish a private channel.

Software is AGPL-3.0-only; documentation/skills have their recorded licenses and
third-party runtime components retain their own licenses. See the distributed
LICENSE, NOTICE, LICENSES and provenance/dependency inventory. These are research
alpha components with the warranty terms in those licenses. No commercial SLA,
official host endorsement or scientific acceptance is offered.
