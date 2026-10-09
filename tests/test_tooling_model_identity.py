# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic structural checks for declared and observed model identity."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import unittest

from agent_braid import tooling_model_identity as identity


def _sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _route_identity(host="codex"):
    auth_method = "chatgpt" if host == "codex" else "claude.ai"
    effective = {"selector": "model-fast-2026-09", "effort": "medium",
                 "providerEndpoint": "https://api.openai.com/v1" if host == "codex" else "https://api.anthropic.com",
                 "authMethod": auth_method,
                 "hostSelection": {"source": "argv", "configRef": None, "flags": ["model-selector", "reasoning-effort"],
                                   "argv": ["selector", "effort"]}}
    return {"kind": "observable-requested-route", "selector": "model-fast-2026-09",
            "selectorKind": "provider-alias", "effort": "medium", "effectiveConfig": effective,
            "configSha256": identity.canonical_json_sha256(effective),
            "cliBuild": {"version": "cli-1.2", "sha256": _sha("cli")},
            "nativeCatalogEntry": {"observedAtUtc": "2026-10-09T08:00:00Z", "sourceRef": "catalog.json",
                                   "catalogSha256": _sha("catalog"), "entrySha256": _sha("entry")},
            "providerRoute": {"provider": "openai" if host == "codex" else "anthropic", "accountSha256": _sha("account"),
                              "authMethod": auth_method},
            "backendAvailable": False, "immutableId": None,
            "backendDigestAvailable": False, "backendSha256": None}


def _observation(identity_data, now):
    catalog = identity_data["nativeCatalogEntry"]
    return identity.ModelIdentityObservation(
        selector_kind=identity_data["selectorKind"], configured_selector=identity_data["selector"], reported_selector=None,
        effort=identity_data["effort"], config_sha256=identity_data["configSha256"],
        catalog_sha256=catalog["catalogSha256"], entry_sha256=catalog["entrySha256"],
        provider_route=identity_data["providerRoute"], backend_available=False, immutable_id=None, backend_sha256=None,
        observed_at_utc=now, source_ref="native-observer", source_sha256=_sha("observation"))


class ModelIdentityTests(unittest.TestCase):
    def test_requested_route_has_explicit_unknown_backend_and_fresh_receipt(self):
        expected = _route_identity()
        model = {"name": expected["selector"], "version": None, "sha256": None}
        identity.validate_identity(expected, host="codex", model=model)
        now = datetime.now(timezone.utc)
        observed = _observation(expected, now)
        self.assertTrue(identity.check_observation(observed, expected, now=now))
        self.assertEqual(identity.observation_from_dict(observed.as_dict()), observed)
        self.assertEqual(identity.entry_sha256({"id": "x", "name": "n"}),
                         identity.canonical_json_sha256({"name": "n", "id": "x"}))
        self.assertEqual(identity.artifact_sha256(b"catalog bytes"), _sha("catalog bytes"))

    def test_v2_model_fields_and_selection_metadata_are_explicit_and_bounded(self):
        expected = _route_identity()
        for model in ({"name": expected["selector"], "sha256": None},
                      {"name": expected["selector"], "version": None},
                      {"name": expected["selector"], "version": None, "sha256": None, "extra": None}):
            with self.subTest(model=model), self.assertRaises(identity.ModelIdentityError):
                identity.validate_identity(expected, host="codex", model=model)
        for field, value in (("argv", ["--api-key", "credential-value"]),
                             ("flags", ["--token"]),
                             ("configRef", "credential-secret-value")):
            bad = dict(expected)
            bad_config = dict(expected["effectiveConfig"])
            selection = dict(bad_config["hostSelection"])
            selection[field] = value
            bad_config["hostSelection"] = selection
            bad["effectiveConfig"] = bad_config
            bad["configSha256"] = identity.canonical_json_sha256(bad_config)
            with self.subTest(field=field), self.assertRaises(identity.ModelIdentityError):
                identity.validate_identity(bad, host="codex", model={"name": bad["selector"], "version": None, "sha256": None})

    def test_route_rejects_model_build_fabrication_and_identity_drift(self):
        expected = _route_identity("claude-code")
        for field, value in (("version", "catalog"), ("sha256", _sha("catalog"))):
            model = {"name": expected["selector"], "version": None, "sha256": None}
            model[field] = value
            with self.subTest(field=field), self.assertRaises(identity.ModelIdentityError):
                identity.validate_identity(expected, host="codex", model=model)
        now = datetime.now(timezone.utc)
        base = _observation(expected, now)
        changed = (replace(base, configured_selector="another-selector"),
                   replace(base, reported_selector="different"),
                   replace(base, effort="high"), replace(base, config_sha256=_sha("changed-config")),
                   replace(base, catalog_sha256=_sha("changed-catalog")),
                   replace(base, entry_sha256=_sha("changed-entry")),
                   replace(base, provider_route={**base.provider_route, "accountSha256": _sha("other-account")} ),
                   replace(base, backend_available=True, immutable_id="provider-build-7"),
                   replace(base, observed_at_utc=now + timedelta(seconds=1)),
                   replace(base, observed_at_utc=now - timedelta(seconds=61)))
        for observed in changed:
            with self.subTest(observed=observed), self.assertRaises(identity.ModelIdentityError):
                identity.check_observation(observed, expected, now=now)

    def test_advertised_immutable_backend_requires_authoritative_id_and_legacy_pin(self):
        expected = _route_identity("claude-code")
        expected.update(kind="immutable-provider-build", selectorKind="provider-alias", backendAvailable=True,
                        immutableId="provider-build-7", backendDigestAvailable=False, backendSha256=None)
        model = {"name": expected["selector"], "version": "provider-build-7", "sha256": None}
        identity.validate_identity(expected, host="claude-code", model=model)
        for malformed in ({**expected, "immutableId": None}, {**expected, "kind": "observable-requested-route"}):
            with self.assertRaises(identity.ModelIdentityError):
                identity.validate_identity(malformed, host="claude-code", model=model)
        expected["backendDigestAvailable"] = True
        expected["backendSha256"] = _sha("actual backend artifact digest")
        model["sha256"] = expected["backendSha256"]
        identity.validate_identity(expected, host="claude-code", model=model)
        model["sha256"] = _sha("catalog digest is not backend digest")
        with self.assertRaises(identity.ModelIdentityError):
            identity.validate_identity(expected, host="claude-code", model=model)
        model["sha256"] = expected["backendSha256"]
        now = datetime.now(timezone.utc)
        observed = replace(_observation(expected, now), selector_kind="provider-alias",
                           backend_available=True, immutable_id=expected["immutableId"],
                           backend_sha256=expected["backendSha256"])
        self.assertTrue(identity.check_observation(observed, expected, now=now))
        for bad in (replace(observed, immutable_id=None), replace(observed, immutable_id="different-id"),
                    replace(observed, backend_sha256=_sha("catalog hash masquerading as backend digest"))):
            with self.assertRaises(identity.ModelIdentityError):
                identity.check_observation(bad, expected, now=now)

    def test_serialized_observation_rejects_unknown_fields_and_naive_timestamp(self):
        expected = _route_identity()
        value = _observation(expected, datetime.now(timezone.utc)).as_dict()
        malformed = {**value, "unrecognized": True}
        with self.assertRaises(identity.ModelIdentityError):
            identity.observation_from_dict(malformed)
        malformed = {**value, "observedAtUtc": "2026-10-09T08:00:00"}
        with self.assertRaises(identity.ModelIdentityError):
            identity.observation_from_dict(malformed)


if __name__ == "__main__":
    unittest.main()
