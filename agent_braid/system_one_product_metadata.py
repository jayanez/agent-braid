# SPDX-License-Identifier: AGPL-3.0-only
"""Package-owned static discovery metadata; no imports of optional implementations."""
from agent_braid.system_one import MODEL_MANIFEST, digest, freeze

COMPILER_MANIFEST = freeze({"capabilityId": "s1-schema-synthetic-v1",
                            "contractVersion": "s1-schema-synthetic-v1",
                            "evidenceClass": "heuristic",
                            "executionAuthorization": False})
CORE_ROUTE_MANIFEST = freeze(MODEL_MANIFEST)
_routes = []
for _language in ("en", "es"):
    for _task in ("boolean-fixture", "choice-fixture", "score-fixture", "schema-compile-fixture"):
        _schema = _task == "schema-compile-fixture"
        _routes.append({"languageTag": _language, "taskId": _task,
                        "capabilityId": "s1-schema-synthetic-v1" if _schema else "synthetic-reference-v1",
                        "backendId": None if _schema else "stdlib-rule-fixture-v1",
                        "policyId": None if _schema else "strict-uncalibrated-v1",
                        "installedManifestDigest": digest(COMPILER_MANIFEST if _schema else CORE_ROUTE_MANIFEST),
                        "supported": True})
_registry = {"version": "s1-metadata-router-v1", "routes": _routes}
ROUTER_REGISTRY = freeze({**_registry, "digest": digest(_registry)})
del _routes, _registry, _language, _task, _schema
