# Native plugin research — 2026-10-16

Reviewed local skill catalog and repository Spec Kit workflows. Applicable workflows: specify/plan/tasks/analyze/taskstoissues/implement, Python API/CLI/testing, skill creation, documentation/ADRs and Luna review. NVIDIA routing has no product relevance here; no additional capability installation is required. Context7 resolve calls returned monthly quota exhaustion; primary official sources were used instead.

- OpenAI plugin packaging/onboarding/user marketplace: https://developers.openai.com/plugins/build/plugins
- OpenAI local MCP eligibility: https://developers.openai.com/plugins/deploy/desktop-only
- OpenAI submission: https://developers.openai.com/plugins/deploy/submission
- Claude plugin manifests: https://code.claude.com/docs/en/plugins-reference
- Claude user install: https://code.claude.com/docs/en/plugins/install
- Anthropic candidacy: https://code.claude.com/docs/en/plugins/publish
- Binary/size restrictions: https://claude.com/docs/plugins/pre-submission-checklist
- Relocatable runtime: https://github.com/astral-sh/python-build-standalone/releases/tag/20261013

Decisions: include relocatable CPython rather than require uv/pip or change sys.executable with a frozen executable; provide one universal local package containing both architectures; use Git distribution before external directory approvals; keep no-dependency experience if a directory refuses the artifact. Official docs and CLI help do not establish observed plugin conformance.

Observed planning CLI versions: Codex 0.163.0-alpha.10.2; Claude Code 2.1.292. Recheck installed versions during acceptance.
