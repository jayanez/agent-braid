# SPEC-060 release record: package 0.1.0a2

Published 2026-10-27 as GitHub pre-release
[`v0.1.0-alpha.2`](https://github.com/jayanez/agent-braid/releases/tag/v0.1.0-alpha.2),
authorized by the owner immediately before the tag. No PyPI upload.

| Item | Value |
|---|---|
| Tag | `v0.1.0-alpha.2` (annotated) |
| Commit | `d9c89eeab3369d1635c029d65a008252b1ab1798` (ancestor of `develop`) |
| Wheel | `agent_braid-0.1.0a2-py3-none-any.whl`, SHA-256 `6272a64576ca307a320aacdef568ec8243c6f2809f23626dabaa673cff69d1a2` |
| Sdist | `agent_braid-0.1.0a2.tar.gz`, SHA-256 `fadfc78707a1f0212931b4369e2bfcdccd3bd69cf10d65235fec493d5ce307c0` |
| Checksums asset | `SHA256SUMS` |

## Verification

- Assets built from the tagged commit in a clean clone (Python 3.12, `build`).
- `scripts/verify_installed_tooling_v2.py --target macos-arm64 --execute-installed`
  under CPython 3.13.11: passed, 28 packages, receipt SHA-256
  `00a3b89d78237f19a4613bb4d931a10e0d7e47008e90da7976250c7d79ee0b1a`.
- Downloaded release assets match `SHA256SUMS`.
- Archive hashes are not reproducible between builds; the table above is the published truth.

## Alias removal countdown (T011, #771; parent #760)

Criteria are in `contracts/interface-delta.md` sections 4.5 and 4.7.
This is release 1 of at least 2 carrying the deprecated `agent-braid-*` aliases.
The 180-day limit from this release ends on **2027-04-25**; by then the owner must decide
explicitly. Removal needs contract `agent-braid-tooling/v0.3` (SPEC amendment and ADR),
a repository search and a surfaces recheck. Nothing is removed by this record.
