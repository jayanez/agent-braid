# ADR 0012: MIT boundary for vendored Python skills

- **Status:** accepted by explicit founder decision on 2026-09-23
- **Date:** 2026-09-23
- **Deciders:** Juan Antonio Yáñez García (founder)
- **Constitutional articles:** 16, 21, 25

## Context

The branch vendors five skills from `wdm0006/python-skills` at commit
`954796b7fc28e342cf08f80b9a4a39414a419c7a` and adapts several entry points
to Agent Braid. The source distributes them under MIT. The repository's existing
license map assigns its own software to `AGPL-3.0-only` and its own documentation
to `CC-BY-SA-4.0`, while requiring third-party material to retain its stated
terms. Because the skills live in documentation-like paths and have been edited,
the applicable boundary needs an explicit decision and notice.

`GOVERNANCE.md` requires a dedicated ADR and explicit founder approval for a
change to the license boundary. Automated validation cannot provide that approval.

## Decision

The founder approved the five vendored and repository-adapted skill directories under
`.agents/skills/` and their exact mirrors under `.claude/skills/` as MIT-covered
third-party material:

- `api-design`
- `cli-development`
- `code-quality`
- `documentation`
- `testing-strategy`

Record their pinned source, author attribution, full MIT permission and copyright
notice, and local adaptations in `VENDORED-SKILLS.md`, `NOTICE`, and
`LICENSES/python-skills-MIT.txt`. Keep the path exception explicit in `LICENSE`.
Redistributions of these skills must preserve the MIT notice and identify local
modifications.

This decision does not relicense project-authored code, validators, tests,
Spec Kit editorial skills, research, or other documentation. Their existing
`AGPL-3.0-only` or `CC-BY-SA-4.0` mapping remains in force. It does not approve
new runtime dependencies, install NVIDIA skills, alter scientific claims, or
authorize a release.

## Alternatives considered

- **Omit the vendored skills:** avoids the additional license category, but loses
  the proposed reusable guidance.
- **Rewrite every skill independently:** could create project-authored material
  under the existing license map, but requires fresh authorship and a separate
  review; it is not a valid way to remove the source's existing notice from
  adapted copies.
- **Leave the path mapping implicit:** permits ambiguity for users and
  redistributors and makes compliance difficult to audit.

## Consequences

The repository has a narrow MIT exception for the named skill directories. The
project must preserve their notice on redistribution and keep both agent copies
synchronized. Future third-party additions or material changes to this boundary
need their own provenance and licensing review. This ADR makes no claim of
independent legal advice or review.

## Validation

The repository validator checks the canonical notice, the explicit path mapping,
skill metadata, local links, and byte parity between the two copies, including
the provenance manifests. The pull request records executable validation results;
those results are technical evidence only. The founder explicitly approved this
bounded license decision on 2026-09-23. Final review of the committed branch
remains separate.

## References

- [Source repository and pinned commit](https://github.com/wdm0006/python-skills/tree/954796b7fc28e342cf08f80b9a4a39414a419c7a)
- [Source MIT license](https://github.com/wdm0006/python-skills/blob/954796b7fc28e342cf08f80b9a4a39414a419c7a/LICENSE)
- [ADR 0003: Copyleft licensing and trademark protection](0003-copyleft-and-trademark-protection.md)
- [Governance decision classes](../../GOVERNANCE.md)
