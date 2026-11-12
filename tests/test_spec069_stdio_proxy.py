# SPDX-License-Identifier: AGPL-3.0-only
"""Offline proxy tests: no host, model, credential or network."""

import hashlib
import json
import os
import select
import signal
import subprocess
import sys
import tempfile
import unittest
import importlib.util
from pathlib import Path

PROXY = Path(__file__).resolve().parents[1] / "scripts/spec069_stdio_proxy.py"
SERVER = r'''
import json, sys
for line in sys.stdin.buffer:
    m = json.loads(line)
    if m.get("method") == "initialize":
        result = {"protocolVersion": "2025-03-26"}
    elif m.get("method") == "tools/list":
        result = {"tools": [{"name": "analyze-work", "description": "PRIVATE-SERVER", "inputSchema": {"type": "object"}}]}
    else:
        result = {"content": "PRIVATE-CALL"}
    sys.stdout.buffer.write(json.dumps({"jsonrpc": "2.0", "id": m["id"], "result": result}, separators=(",", ":")).encode() + b"\n")
    sys.stdout.buffer.flush()
'''


class ProxyTests(unittest.TestCase):
    def test_transparent_and_private_per_connection_receipt(self):
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "analyze-work", "arguments": {"request": {"secret": "PRIVATE-REQUEST"}}}},
        ]
        data = b"".join(json.dumps(m).encode() + b"\n" for m in messages)
        direct = subprocess.run([sys.executable, "-c", SERVER], input=data, capture_output=True, timeout=10, check=True)
        with tempfile.TemporaryDirectory() as temp:
            receipt = Path(temp) / "receipt.json"
            run = subprocess.run([sys.executable, str(PROXY), "--receipt", str(receipt), "--", sys.executable, "-c", SERVER],
                                 input=data, capture_output=True, timeout=10, check=True)
            self.assertEqual(run.stdout, direct.stdout)
            raw = receipt.read_text()
            self.assertNotIn("PRIVATE-", raw)
            self.assertEqual(os.stat(receipt).st_mode & 0o777, 0o600)
            evidence = json.loads(raw)
            self.assertEqual(evidence["protocolVersion"], "2025-03-26")
            listing = direct.stdout.splitlines(keepends=True)[1]
            self.assertEqual(evidence["listings"][0]["lineSha256"], hashlib.sha256(listing).hexdigest())
            self.assertEqual(evidence["calls"][0]["requestType"], "object")
            self.assertTrue(evidence["complete"])

    def test_no_overwrite_and_failed_child_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            receipt = Path(temp) / "receipt.json"
            receipt.write_text("untouched")
            command = [sys.executable, str(PROXY), "--receipt", str(receipt), "--", sys.executable, "-c", "raise SystemExit(7)"]
            result = subprocess.run(command, input=b"", capture_output=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(receipt.read_text(), "untouched")
            receipt.unlink()
            result = subprocess.run(command, input=b"", capture_output=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(json.loads(receipt.read_text())["complete"])

    def test_invalid_line_does_not_leak_and_is_not_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            receipt = Path(temp) / "receipt.json"
            server = "import sys; sys.stdout.buffer.write(b'PRIVATE-INVALID\\n'); sys.stdout.flush()"
            result = subprocess.run([sys.executable, str(PROXY), "--receipt", str(receipt), "--", sys.executable, "-c", server],
                                    input=b"", capture_output=True, timeout=10)
            self.assertEqual(result.stdout, b"PRIVATE-INVALID\n")
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("PRIVATE", receipt.read_text())
            self.assertFalse(json.loads(receipt.read_text())["complete"])

    def test_oversize_input_fails_closed_and_stops_server(self):
        with tempfile.TemporaryDirectory() as temp:
            receipt = Path(temp) / "receipt.json"
            server = "import sys,time; sys.stdin.buffer.read(); time.sleep(60)"
            result = subprocess.run([sys.executable, str(PROXY), "--receipt", str(receipt), "--", sys.executable, "-c", server],
                                    input=b"x" * (1024 * 1024 + 1), capture_output=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("line_limit", json.loads(receipt.read_text())["errors"])

    def test_missing_target_definition_is_not_valid_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            receipt = Path(temp) / "receipt.json"
            server = 'import sys; sys.stdin.readline(); print(\'{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}\', flush=True)'
            message = b'{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n'
            result = subprocess.run([sys.executable, str(PROXY), "--receipt", str(receipt), "--", sys.executable, "-c", server],
                                    input=message, capture_output=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(json.loads(receipt.read_text())["complete"])

    def test_result_hash_is_independent_of_rpc_id(self):
        with tempfile.TemporaryDirectory() as temp:
            receipts = []
            for ident in (2, 99):
                receipt = Path(temp) / f"{ident}.json"
                message = json.dumps({"jsonrpc": "2.0", "id": ident, "method": "tools/list"}).encode() + b"\n"
                subprocess.run([sys.executable, str(PROXY), "--receipt", str(receipt), "--", sys.executable, "-c", SERVER],
                               input=message, capture_output=True, timeout=10, check=True)
                receipts.append(json.loads(receipt.read_text())["listings"][0])
            self.assertNotEqual(receipts[0]["lineSha256"], receipts[1]["lineSha256"])
            self.assertEqual(receipts[0]["resultCanonicalSha256"], receipts[1]["resultCanonicalSha256"])
            self.assertEqual(receipts[0]["analyzeWorkCanonicalSha256"], receipts[1]["analyzeWorkCanonicalSha256"])

    def test_termination_stops_server_and_marks_receipt_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            receipt = Path(temp) / "receipt.json"
            server = "import os,sys,time; print(os.getpid(), flush=True); time.sleep(60)"
            proc = subprocess.Popen([sys.executable, str(PROXY), "--receipt", str(receipt), "--", sys.executable, "-c", server],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                self.assertTrue(select.select([proc.stdout], [], [], 10)[0])
                pid = int(proc.stdout.readline())
                proc.send_signal(signal.SIGTERM)
                self.assertNotEqual(proc.wait(timeout=10), 0)
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)
                self.assertFalse(json.loads(receipt.read_text())["complete"])
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
                for stream in (proc.stdin, proc.stdout, proc.stderr):
                    stream.close()

    @unittest.skipUnless(importlib.util.find_spec("mcp"), "project optional MCP dependency not installed")
    def test_real_plugin_listing_without_host_or_model(self):
        from agent_braid.plugin_registry import plan_setup, apply
        with tempfile.TemporaryDirectory() as temp:
            receipt = Path(temp).resolve() / "receipt.json"
            home = Path(temp).resolve() / "home"
            home.mkdir()
            repo = home / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            preview = plan_setup(home / "braid", [repo])
            apply(home / "braid", preview, preview["previewDigest"])
            env = {"HOME": str(home), "PATH": os.environ.get("PATH", ""), "XDG_CONFIG_HOME": str(home / "config"),
                   "XDG_DATA_HOME": str(home / "data"), "XDG_STATE_HOME": str(home / "state")}
            command = [sys.executable, str(PROXY), "--receipt", str(receipt), "--", sys.executable, "-m", "agent_braid",
                       "plugin", "serve", "--home", str(home / "braid")]
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            try:
                def exchange(message):
                    process.stdin.write(json.dumps(message).encode() + b"\n")
                    process.stdin.flush()
                    self.assertTrue(select.select([process.stdout], [], [], 10)[0], "plugin response timed out")
                    return json.loads(process.stdout.readline())
                init = exchange({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "offline-test", "version": "1"}}})
                process.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
                process.stdin.flush()
                listing = exchange({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
                self.assertTrue(any(t["name"] == "analyze-work" for t in listing["result"]["tools"]))
                self.assertIn("protocolVersion", init["result"])
                process.stdin.close()
                self.assertEqual(process.wait(timeout=10), 0)
                evidence = json.loads(receipt.read_text())
                self.assertTrue(evidence["complete"])
                self.assertEqual(evidence["protocolVersion"], init["result"]["protocolVersion"])
                self.assertIsNotNone(evidence["listings"][0]["analyzeWorkCanonicalSha256"])
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                process.stdout.close()
                process.stderr.close()


if __name__ == "__main__":
    unittest.main()
