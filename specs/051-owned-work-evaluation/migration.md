# Compatibility and migration

Additive experimental Python modules and two isolated schema contracts; no public
re-export, package dependency, CLI, MCP, plugin default or existing schema change.
SPEC-045 REQ-001/004 and `authentic-on-synthetic` recorder remain unchanged.
SPEC-047's closed numeric rows/default-off state remain unchanged; projection is
always none. Typed-v1 flat .txt / 2–4-operation domain is unchanged. No existing
records are converted or relabeled. Schema publication requires its own reviewed
PR under Governance; local owner-authorized implementation is not publication.
Architecture decision: keep validation pure and caller-supplied trust distinct
from secure storage and capture (ADR 0026). All source admission remains pending.
