# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-080/T006 controls: OpenCode in the harness host inventory, gates unchanged.

OpenCode joins the inventory host lists (``harness_components.HOSTS`` and
``HOST_SUPPORT``) as unqualified with no observed build. Every native gate keeps an
explicit Claude and Codex set (``GATED_HOSTS``): hook matrices and hook records, tool
contracts, the advisory ``capabilities`` host rows, the lifecycle hosts and the T008
host-profile gate. ``tests/fixtures/harness_t006`` holds records built from the base
code before the change; they must still verify byte for byte. Each new guard has one
mutation control that loads a copy of its module with that guard textually undone.
"""
import ast
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest

from agent_braid import harness_advisory as ha
from agent_braid import harness_components as hc
from agent_braid import harness_hooks as hk
from agent_braid import harness_hosts as hh
from agent_braid import harness_lifecycle as hl
from agent_braid import harness_tools as ht
from agent_braid.harness_manifest import NATIVE_BUILD
from agent_braid.system_one import canonical, digest
from tests.test_harness_components import _compile, file_row, make_inventory
from tests.test_harness_promotion import HUMAN, IDENTITY, SCOPE

PACKAGE = Path(hc.__file__).parent
FIXTURES = Path(__file__).parent / "fixtures" / "harness_t006"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
GATE_ROWS = {"claude": {"observedBuild": NATIVE_BUILD, "qualification": "unqualified"},
             "codex": {"observedBuild": None, "qualification": "unqualified"}}
OPENCODE_ROW = {"observedBuild": None, "qualification": "unqualified"}


def fixture(name):
    raw = (FIXTURES / name).read_bytes()
    return raw, MANIFEST["files"][name]


def mutant(module, old, new):
    """Load a separate copy of ``module`` with one guard textually replaced."""
    path = Path(module.__file__)
    source = path.read_text(encoding="utf-8")
    assert source.count(old) == 1, old
    name = f"agent_braid._t006_mutant_{path.stem}"
    copy = types.ModuleType(name)
    copy.__package__ = "agent_braid"
    sys.modules[name] = copy
    try:
        exec(compile(source.replace(old, new), str(path), "exec"), copy.__dict__)
    finally:
        del sys.modules[name]
    return copy


class Refuses(unittest.TestCase):
    def refuses(self, error, reason, fn, *args, **kwargs):
        with self.assertRaises(error) as caught:
            fn(*args, **kwargs)
        self.assertEqual(caught.exception.reason, reason)


class InventoryTests(Refuses):
    def test_opencode_is_present_and_unqualified_in_the_inventory(self):
        self.assertEqual(hc.HOSTS, ("claude", "codex", "opencode"))
        self.assertEqual(hc.HOST_SUPPORT, {**GATE_ROWS, "opencode": OPENCODE_ROW})
        self.assertEqual(tuple(hc.HOST_SUPPORT), hc.HOSTS)

    def test_gate_set_is_claude_and_codex_with_unchanged_rows(self):
        self.assertEqual(hc.GATED_HOSTS, ("claude", "codex"))
        self.assertEqual(hc.GATED_HOST_SUPPORT, GATE_ROWS)
        self.assertNotIn("opencode", hc.GATED_HOST_SUPPORT)
        # The gate rows are independent copies: editing them cannot reach the inventory.
        self.assertIsNot(hc.GATED_HOST_SUPPORT["claude"], hc.HOST_SUPPORT["claude"])

    def test_t008_host_profile_gate_stays_on_claude_and_codex(self):
        self.assertEqual(hh.GATED_HOSTS, hc.GATED_HOSTS)
        self.assertFalse(hasattr(hh, "HOSTS"))
        self.refuses(hh.HostGateError, "invalid-observation", hh.QuotaObservation,
                     "opencode", 1, "max", "subscription", 0, 2, 0, 2, False)
        hh.QuotaObservation("codex", 1, "max", "subscription", 0, 2, 0, 2, False)

    def test_t008_gate_mutation_control(self):
        m = mutant(hh, 'GATED_HOSTS = ("claude", "codex")',
                   'GATED_HOSTS = ("claude", "codex", "opencode")')
        m.QuotaObservation("opencode", 1, "max", "subscription", 0, 2, 0, 2, False)

    def test_every_host_list_importer_is_classified(self):
        """Inventory names may be read only where the T006 table says inventory."""
        seen = {}
        for path in sorted(PACKAGE.glob("*.py")):
            if path.name == "harness_components.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module == "harness_components":
                    names |= {a.name for a in node.names}
                elif (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                      and node.value.id == "hc"):
                    names.add(node.attr)
            used = names & {"HOSTS", "HOST_SUPPORT", "GATED_HOSTS", "GATED_HOST_SUPPORT"}
            if used:
                seen[path.stem] = used
        self.assertEqual(seen, {
            "harness_advisory": {"GATED_HOST_SUPPORT"},
            "harness_hooks": {"GATED_HOSTS", "GATED_HOST_SUPPORT"},
            "harness_lifecycle": {"GATED_HOSTS", "HOST_SUPPORT"},
            "harness_tools": {"GATED_HOST_SUPPORT"},
        })


class LifecycleTests(Refuses):
    def test_opencode_is_not_lifecycle_supported(self):
        self.assertEqual(hl.SUPPORTED_HOSTS, ("claude",))
        self.assertNotIn("opencode", hl.SUPPORTED_HOSTS)

    def test_lifecycle_install_for_opencode_refuses(self):
        args = {"opt_in": True, "operator": HUMAN, "scope": SCOPE, "identity": IDENTITY, "at": 1}
        with tempfile.TemporaryDirectory() as tmp:
            for host in ("opencode", "codex"):
                self.refuses(hl.LifecycleError, "unsupported-host", hl.install, Path(tmp),
                             host=host, **args)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), [])
            hl.install(Path(tmp), host="claude", **args)  # positive control: same arguments

    def test_an_observed_opencode_build_still_gives_no_lifecycle_support(self):
        support = {**GATE_ROWS, "opencode": {"observedBuild": "1.0.0",
                                             "qualification": "unqualified"}}
        self.assertEqual(hl.lifecycle_hosts(support), ("claude",))
        self.assertEqual(hl.lifecycle_hosts(hc.HOST_SUPPORT), hl.SUPPORTED_HOSTS)

    def test_lifecycle_gate_mutation_control(self):
        m = mutant(hl, "for h in hc.GATED_HOSTS", "for h in hc.HOST_SUPPORT")
        support = {**GATE_ROWS, "opencode": {"observedBuild": "1.0.0",
                                             "qualification": "unqualified"}}
        self.assertIn("opencode", m.lifecycle_hosts(support))


class HookTests(Refuses):
    def test_opencode_hook_matrix_refuses_unknown_host(self):
        self.refuses(hc.ProfileError, "unknown-host", hk.matrix_record, "opencode")
        self.refuses(hc.ProfileError, "unknown-host", hk.event_status, "opencode", "PreToolUse")
        forged = dict(hk.matrix_record("codex"), host="opencode")
        raw = canonical(forged)
        self.refuses(hc.ProfileError, "matrix-forged", hk.verify_matrix, raw,
                     expected_sha256=sha256(raw).hexdigest())

    def test_opencode_hook_record_refuses_unknown_host(self):
        raw, _ = fixture("hookset-v0.1.json")
        record = dict(json.loads(raw), host="opencode")
        self.refuses(hc.ProfileError, "unknown-host", hk.parse_hookset, canonical(record))
        spec = {key: record[key] for key in record if key not in (
            "hostSupport", "matrixSha256", "inputSha256", "policies", "admission")}
        spec["format"] = hk.SPEC_FORMAT
        self.refuses(hc.ProfileError, "unknown-host", hk.compile_hookset, canonical(spec),
                     expected_input_sha256=sha256(canonical(spec)).hexdigest())

    def test_pre_change_hook_record_and_matrices_verify(self):
        raw, sha = fixture("hookset-v0.1.json")
        hookset = hk.verify_hookset(raw, expected_sha256=sha)
        self.assertEqual(hookset.canonical_bytes, raw)
        self.assertEqual(hookset.data["hostSupport"], GATE_ROWS)
        for host in hc.GATED_HOSTS:
            raw, sha = fixture(f"hook-matrix-{host}.json")
            self.assertEqual(canonical(hk.matrix_record(host)), raw)
            hk.verify_matrix(raw, expected_sha256=sha)

    def test_hook_gate_mutation_control(self):
        m = mutant(hk, "GATED_HOST_SUPPORT, GATED_HOSTS, ProfileError",
                   "HOST_SUPPORT as GATED_HOST_SUPPORT, HOSTS as GATED_HOSTS, ProfileError")
        raw, sha = fixture("hookset-v0.1.json")
        self.refuses(hc.ProfileError, "host-build-drift", m.verify_hookset, raw,
                     expected_sha256=sha)
        with self.assertRaises(KeyError):
            m.matrix_record("opencode")


class ToolAndAdvisoryTests(Refuses):
    def test_pre_change_tool_contract_verifies(self):
        raw, sha = fixture("tool-contract-v0.1.json")
        contract = ht.verify_contract(raw, expected_sha256=sha)
        self.assertEqual(contract.canonical_bytes, raw)
        self.assertEqual(contract.data["hostSupport"], GATE_ROWS)

    def test_tool_gate_mutation_control(self):
        m = mutant(ht, "GATED_HOST_SUPPORT, PROTECTED_COMPONENTS",
                   "HOST_SUPPORT as GATED_HOST_SUPPORT, PROTECTED_COMPONENTS")
        raw, sha = fixture("tool-contract-v0.1.json")
        self.refuses(hc.ProfileError, "host-build-drift", m.verify_contract, raw,
                     expected_sha256=sha)

    def test_advisory_capabilities_output_is_unchanged(self):
        raw, sha = fixture("advisory-capabilities.json")
        self.assertEqual(canonical(ha._capabilities()), raw)
        self.assertEqual(sha256(raw).hexdigest(), sha)

    def test_advisory_gate_mutation_control(self):
        m = mutant(ha, "CLASSES, GATED_HOST_SUPPORT, ROOTS",
                   "CLASSES, HOST_SUPPORT as GATED_HOST_SUPPORT, ROOTS")
        raw, _ = fixture("advisory-capabilities.json")
        self.assertNotEqual(canonical(m._capabilities()), raw)


class ProfileTests(Refuses):
    def test_pre_change_profiles_verify_as_legacy_without_upgrade(self):
        for name in ("profile-v0.1.json", "profile-v0.1-child.json"):
            raw, sha = fixture(name)
            profile = hc.verify_profile(raw, expected_sha256=sha)
            self.assertEqual(profile.canonical_bytes, raw, name)
            self.assertEqual(profile.data["format"], hc.LEGACY_FORMAT)
            self.assertEqual(profile.data["hostSupport"], GATE_ROWS)

    def test_new_profiles_are_v0_2_with_three_rows(self):
        data = _compile(make_inventory()).to_dict()
        self.assertEqual(hc.FORMAT, "braid-harness-profile/v0.2")
        self.assertEqual(data["format"], hc.FORMAT)
        self.assertEqual(data["hostSupport"], {**GATE_ROWS, "opencode": OPENCODE_ROW})

    def test_child_of_a_legacy_parent_compiles_as_v0_2(self):
        raw, sha = fixture("profile-v0.1.json")
        rows = [file_row("guidance/a.md", b"a", "inherit"), file_row("guidance/b.md", b"b", "inherit"),
                file_row("guidance/z.md", b"z")]
        child = _compile(make_inventory(rows, version=2, parentSha256=sha),
                         parent_raw=raw, expected_parent_sha256=sha)
        self.assertEqual((child.data["format"], child.data["parentSha256"]), (hc.FORMAT, sha))
        self.assertEqual(child.data["hostSupport"], {**GATE_ROWS, "opencode": OPENCODE_ROW})

    def test_host_rows_must_match_the_record_format(self):
        legacy = json.loads(fixture("profile-v0.1.json")[0])
        upgraded = dict(legacy, hostSupport={**GATE_ROWS, "opencode": OPENCODE_ROW})
        self.refuses(hc.ProfileError, "invalid-profile", hc.parse_profile, canonical(upgraded))
        current = _compile(make_inventory()).to_dict()
        two_rows = dict(current, hostSupport=GATE_ROWS)
        self.refuses(hc.ProfileError, "invalid-profile", hc.parse_profile, canonical(two_rows))
        drift = dict(current, hostSupport={**GATE_ROWS, "opencode": {
            "observedBuild": "1.0.0", "qualification": "unqualified"}})
        self.refuses(hc.ProfileError, "host-build-drift", hc.parse_profile, canonical(drift))
        future = dict(current, format="braid-harness-profile/v0.3")
        self.refuses(hc.ProfileError, "unsupported-version", hc.parse_profile, canonical(future))

    def test_opencode_profile_is_known_but_refused(self):
        self.refuses(hc.ProfileError, "host-refused", _compile, make_inventory(host="opencode"))
        current = _compile(make_inventory()).to_dict()
        self.refuses(hc.ProfileError, "host-refused", hc.parse_profile,
                     canonical(dict(current, host="opencode")))

    def test_legacy_reading_mutation_control(self):
        m = mutant(hc, "_HOST_ROWS = {FORMAT: HOST_SUPPORT, LEGACY_FORMAT: GATED_HOST_SUPPORT}",
                   "_HOST_ROWS = {FORMAT: HOST_SUPPORT}")
        raw, sha = fixture("profile-v0.1.json")
        with self.assertRaises(m.ProfileError) as caught:
            m.verify_profile(raw, expected_sha256=sha)
        self.assertEqual(caught.exception.reason, "unsupported-version")

    def test_legacy_rows_mutation_control(self):
        m = mutant(hc, "_HOST_ROWS = {FORMAT: HOST_SUPPORT, LEGACY_FORMAT: GATED_HOST_SUPPORT}",
                   "_HOST_ROWS = {FORMAT: HOST_SUPPORT, LEGACY_FORMAT: HOST_SUPPORT}")
        legacy = json.loads(fixture("profile-v0.1.json")[0])
        upgraded = dict(legacy, hostSupport={**GATE_ROWS, "opencode": OPENCODE_ROW})
        self.assertEqual(m.parse_profile(canonical(upgraded)).data["format"], m.LEGACY_FORMAT)


class FixtureTests(unittest.TestCase):
    def test_fixture_manifest_matches_the_committed_bytes(self):
        self.assertIs(MANIFEST["executionAuthorization"], False)
        names = sorted(p.name for p in FIXTURES.iterdir() if p.name != "manifest.json")
        self.assertEqual(names, sorted(MANIFEST["files"]))
        for name, expected in MANIFEST["files"].items():
            self.assertEqual(sha256((FIXTURES / name).read_bytes()).hexdigest(), expected, name)
        self.assertEqual(digest(MANIFEST["files"]), digest(dict(sorted(MANIFEST["files"].items()))))


if __name__ == "__main__":
    unittest.main()
