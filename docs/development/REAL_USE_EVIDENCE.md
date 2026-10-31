<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Real-use evidence sources

**Status:** owner instruction, recorded 2026-10-31.
**Applies to:** every task, verification or approval packet that needs real (non-synthetic)
observations of Agent Braid.

## Owner instruction

On 2026-10-31 the owner instructed that every verification relying on real,
non-synthetic evidence use all available Agent Braid telemetry and usage data. This
covers this repository and every other repository where Agent Braid is installed and
configured. The same data serves as evidence for any approval decision a task
requires. Original wording: "que se use toda la información disponible en la telemetría
de agent braid de este repo y de cualquier otro en el que lo tengamos instalado y
configurado para cualquier verificación basada en evidencias reales no sintéticas y
para que sirvan de evidencia para eventuales decisiones de aprobación que requiera
cualquier tarea".

## Rule

Before closing a task, verifying a requirement or preparing a human, founder or owner
decision packet that needs real observations:

1. Query every source below that exists on the operator's machine.
2. Commit a derived receipt to the task's evidence directory. The receipt records the
   sources consulted, the observation window, counts, host, plugin or package version
   when readable, and outcomes.
3. If no source has relevant observations, say so explicitly: list each source checked,
   with the result "no observations". Do not fall back silently to synthetic evidence.

Synthetic fixtures remain valid for their own domain. They do not replace this query
when a task asks for real use.

## Sources

| Source | Location | Access |
|---|---|---|
| Local technical telemetry (SPEC-047) | `~/.local/share/agent-braid/telemetry/metrics.sqlite3` | `agent-braid telemetry status|report --format json`; `export FILE` only to a private destination outside repositories |
| Local evidence, coordination and identity stores | `~/.local/share/agent-braid/{evidence,coordination,identity}/` | Read-only |
| Runtime state | `~/.local/state/agent-braid/` | Read-only |
| Plugin workspace registry and results | `~/Library/Application Support/AgentBraid/` (macOS) | Read-only; the registry lists every repository where the plugin is configured |
| Claude Code host transcripts | `~/.claude/projects/**/*.jsonl` | Through the SPEC-053 transcript adapter |
| Codex host sessions | `~/.codex/sessions/` | Read-only |

The telemetry store keeps 30 UTC days of data. When a decision may need older
observations, export a snapshot early to a private location outside every repository.

## Boundaries

- **Evidence class.** These are *observational real-use* records. They are not
  preregistered, not randomized and not bound to a frozen candidate unless the version
  is readable in the record. They support only the domain they observe (constitution
  clause on evidence domains; `AGENTS.md`).
- **Approval stays human.** Receipts inform decisions; they never grant one. A frozen
  gate or validation plan accepts this class only after an explicit owner amendment
  for that gate, as the M4.5 decision of 2026-10-31 did for SPEC-041 and SPEC-043.
- **Privacy.** Read only. Commit derived, minimal receipts: hashed or redacted session
  IDs, timestamps, tool and skill names, versions, counts and outcomes. Never commit raw
  prompts, transcript content, file contents, credentials, or paths that identify other
  projects. Telemetry stays numeric. Nothing is uploaded.
- **No collection changes.** Agents do not enable, widen, purge or reconfigure collection
  or consent settings to obtain evidence.
