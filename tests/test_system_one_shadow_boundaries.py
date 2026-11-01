# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 T019: the shadow module stays opt-in, offline, model-free and non-authorizing."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SHADOW_PATHS = (ROOT / "agent_braid/system_one_shadow.py", ROOT / "agent_braid/system_one_cli.py")
NETWORK_MODULES = {
    "socket", "ssl", "http", "urllib", "urllib3", "ftplib", "smtplib", "poplib", "imaplib", "telnetlib",
    "xmlrpc", "socketserver", "asyncio", "requests", "httpx", "aiohttp", "websockets", "grpc",
}
MODEL_MODULES = {
    "anthropic", "openai", "torch", "tensorflow", "transformers", "sklearn", "numpy", "scipy", "pandas",
    "jax", "keras", "xgboost", "lightgbm", "onnx", "onnxruntime", "llama_cpp", "langchain", "huggingface_hub",
}

OFF_PROBE = """
import json, sys, tempfile, threading
from pathlib import Path
import agent_braid.cli, agent_braid.plugin_mcp, agent_braid.tooling_mcp as mcp
base = Path(tempfile.mkdtemp()).resolve()
(base / "source").mkdir(); (base / "results").mkdir()
service = mcp.ToolingService(mcp.ToolingConfig(base / "source", base / "results"))
request = json.loads(Path(sys.argv[1]).read_text())
status = service.invoke("analyze-work", {"kind": "aim", "request": request}, threading.Event())["status"]
loaded = sorted(name for name in sys.modules if "system_one_shadow" in name)
print(json.dumps({"status": status, "loaded": loaded}))
"""


def imported_roots(path: Path) -> set[str]:
    """Top-level module names imported anywhere in the file, including function-local imports."""
    roots = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


class ShadowBoundaryTests(unittest.TestCase):
    def test_off_never_imports_the_shadow_module(self):
        sample = ROOT / "examples/analysis/file-edits.json"
        completed = subprocess.run([sys.executable, "-c", OFF_PROBE, str(sample)], cwd=ROOT, check=True,
                                   capture_output=True, text=True, timeout=60)
        result = json.loads(completed.stdout.strip().splitlines()[-1])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["loaded"], [])

    def test_probe_detects_the_module_when_shadow_is_on(self):
        probe = OFF_PROBE.replace("mcp.ToolingConfig(base / \"source\", base / \"results\")",
                                  "mcp.ToolingConfig(base / \"source\", base / \"results\", system_one=\"shadow\")")
        with tempfile.TemporaryDirectory() as home:
            completed = subprocess.run([sys.executable, "-c", probe, str(ROOT / "examples/analysis/file-edits.json")],
                                       cwd=ROOT, check=True, capture_output=True, text=True, timeout=60,
                                       env={"PATH": "/usr/bin:/bin", "HOME": home})
        self.assertEqual(json.loads(completed.stdout.strip().splitlines()[-1])["loaded"],
                         ["agent_braid.system_one_shadow"])

    def test_shadow_paths_import_no_network_or_model_module(self):
        for path in SHADOW_PATHS:
            with self.subTest(path=path.name):
                roots = imported_roots(path)
                self.assertEqual(roots & NETWORK_MODULES, set())
                self.assertEqual(roots & MODEL_MODULES, set())

    def test_shadow_module_has_no_dynamic_import_escape(self):
        for path in SHADOW_PATHS:
            with self.subTest(path=path.name):
                source = path.read_text()
                self.assertNotRegex(source, r"\b__import__\s*\(|\bimportlib\b")

    def test_no_shadow_path_enables_execution_authorization(self):
        enabled = re.compile(r"""["']executionAuthorization["']\s*[:=]\s*True|executionAuthorization\s*=\s*True""")
        for path in SHADOW_PATHS:
            with self.subTest(path=path.name):
                self.assertIsNone(enabled.search(path.read_text()))
        for path in sorted((ROOT / "specs/066-system-one-shadow").rglob("*.json")):
            with self.subTest(path=path.name):
                self.assertNotRegex(path.read_text(), r'"executionAuthorization"\s*:\s*true')

    def test_product_dependencies_stay_empty(self):
        self.assertRegex((ROOT / "pyproject.toml").read_text(), r"(?m)^dependencies\s*=\s*\[\s*\]")


if __name__ == "__main__":
    unittest.main()
