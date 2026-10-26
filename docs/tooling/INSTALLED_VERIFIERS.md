# Installed-package verifiers

Two scripts install a frozen wheel offline into private CPython environments and
probe it through the pinned SDK client. Choose by the portable surface contract the
candidate implements. Neither builds a candidate, and each refuses to install
unless `--execute-installed` is supplied.

| Contract | Package | Prompt roster checked | Script |
|---|---|---|---|
| `agent-braid-tooling/v0.1` | `0.1.0a1` | `agent-braid-analyze`, `agent-braid-plan`, `agent-braid-evidence` | `scripts/verify_installed_tooling.py` |
| `agent-braid-tooling/v0.2` ([SPEC-060](../../specs/060-portable-prompt-names/spec.md)) | `0.1.0a2` | `analyze`, `plan`, `evidence` plus the three `agent-braid-*` names, each marked deprecated | `scripts/verify_installed_tooling_v2.py` |

`verify_installed_tooling.py` is not edited: its SHA-256
(`e88e030718c87fb080f091e7179636e02d416b48a85e2353a00928eecf1ce431`) is recorded
in frozen evidence, so any change would break those records. Run against a v0.2
candidate it stops at the candidate identity check or at "prompt roster", which is
expected.

`verify_installed_tooling_v2.py` loads the v0.1 script unmodified and replaces two
things only: the pinned candidate version (`0.1.0a2`) and the prompt block of the
generated SDK probe. If the v0.1 probe text ever changes, the adapter refuses to
guess and stops. Offline install, relay, bounds and the receipt layout are
inherited, so the receipt schema string is still
`agent-braid-installed-tooling-probe/v1`.

Both checks are structural. They do not observe a native host, and a passing run is
not an owner release decision.
