# Public research-preview cutover audit — 2026-09-25

This is a later observation of the remote state. It does not rewrite the
pre-publication readiness record in `docs/releases/publication-cutover.json`,
the frozen founder review, or the clean-export manifest.

| Cutover condition | Observed state | Read-only source |
| --- | --- | --- |
| Clean public destination | `jayanez/agent-braid` is public, unarchived, and has `develop` as its default branch. Its public root is checked by portable validation. | GitHub repository API; `scripts/validate_spec_kit.py` in a clean clone |
| Public branches | `develop` and `main` exist and both report branch protection. | GitHub branches and branch-protection APIs |
| Release tag | `v0.1.0-alpha.1` exists at `55d0e122eaad586afdbfd1422e2d6c487c571048`. | GitHub tags API |
| Prerelease | `Agent Braid v0.1.0-alpha.1` was published on 2026-09-21 and remains a prerelease. Its description says `independent_validation: pending`. | GitHub Releases API |
| Private history | `jayanez/agent-braid-private-archive` is private and archived. | GitHub repository API |
| Security configuration | Public repository secret scanning, push protection, Dependabot security updates, and vulnerability alerts are enabled. | GitHub repository and vulnerability-alert APIs |

This audit establishes the listed **current remote states**, not who authorized
each historical operation or whether every setting was continuously effective
since cutover. The original remote-operation authorization record remains a
pre-publication plan with `authorized: false` and `executed: false`. An explicit
founder decision bound to this reconciliation is still needed before closing
SPEC-009/T009 and its parent. The publication does not establish independent
validation, production safety, or authority to execute or integrate work.
