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
from scripts import spec069_stdio_proxy as proxy

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


class CorrelationTests(unittest.TestCase):
    def send(self, observer, direction, **message):
        observer.feed(direction, json.dumps({"jsonrpc": "2.0", **message}).encode() + b"\n")

    def test_bidirectional_id_collision_does_not_consume_listing(self):
        observer = proxy.Observer()
        self.send(observer, "in", id=7, method="tools/list")
        self.send(observer, "out", id=7, method="sampling/createMessage", params={"secret": "PRIVATE-PROMPT"})
        self.send(observer, "in", id=7, result={"secret": "PRIVATE-RESPONSE"})
        self.assertEqual(observer.receipt["listings"], [])
        self.assertTrue(observer.pending)
        self.send(observer, "out", id=7, result={"tools": [{"name": "analyze-work"}]})
        self.assertEqual(len(observer.receipt["listings"]), 1)
        self.assertFalse(observer.pending)
        self.assertNotIn("PRIVATE", json.dumps(observer.receipt))

    def test_forged_request_with_result_is_never_a_response(self):
        observer = proxy.Observer()
        self.send(observer, "in", id=1, method="tools/list")
        self.send(observer, "out", id=1, method="sampling/createMessage", result={"tools": [{"name": "analyze-work"}]})
        self.assertEqual(observer.receipt["listings"], [])
        self.assertTrue(observer.pending)
        self.assertTrue(observer.receipt["errors"])

    def test_duplicate_and_invalid_client_request_ids_fail_closed(self):
        for bad in (None, True, 1.5, [], "x" * 129):
            with self.subTest(bad=bad):
                observer = proxy.Observer()
                self.send(observer, "in", id=bad, method="tools/call", params={"name": "analyze-work"})
                self.assertTrue(observer.receipt["errors"])
        observer = proxy.Observer()
        self.send(observer, "in", id="PRIVATE-ID", method="tools/list")
        self.send(observer, "in", id="PRIVATE-ID", method="tools/call", params={"name": "analyze-work"})
        self.assertTrue(observer.receipt["errors"])
        self.assertNotIn("PRIVATE-ID", json.dumps(observer.receipt))

    def test_unrelated_request_cannot_reuse_pending_id(self):
        observer = proxy.Observer()
        self.send(observer, "in", id=1, method="other/request")
        self.send(observer, "in", id=1, method="tools/list")
        self.assertTrue(observer.receipt["errors"])
        self.send(observer, "out", id=1, result={"tools": [{"name": "analyze-work"}]})
        self.assertEqual(observer.receipt["listings"], [])

    def test_invalid_responses_leave_request_pending_without_leaking_payload(self):
        for response in ({"id": 1, "result": {}, "error": {"message": "PRIVATE-ERROR"}},
                         {"id": 1}, {"id": None, "result": {}}, {"id": True, "result": {}}):
            with self.subTest(response=response):
                observer = proxy.Observer()
                self.send(observer, "in", id=1, method="tools/call", params={"name": "analyze-work"})
                self.send(observer, "out", **response)
                self.assertTrue(observer.receipt["errors"])
                self.assertTrue(observer.pending)
                self.assertNotIn("PRIVATE", json.dumps(observer.receipt))

    def test_call_response_completes_only_matching_server_response(self):
        observer = proxy.Observer()
        self.send(observer, "in", id="call", method="tools/call", params={"name": "analyze-work", "arguments": {"request": {}}})
        self.send(observer, "out", id="call", result={"content": [{"text": "PRIVATE-RESULT"}]})
        self.assertFalse(observer.pending)
        self.assertFalse(observer.receipt["errors"])
        self.assertNotIn("PRIVATE", json.dumps(observer.receipt))

    def test_non_json_constants_and_overflow_rejected_in_both_directions(self):
        for direction in ("in", "out"):
            for value in (b"NaN", b"Infinity", b"-Infinity", b"1e400"):
                with self.subTest(direction=direction, value=value):
                    observer = proxy.Observer()
                    observer.feed(direction, b'{"jsonrpc":"2.0","method":"notifications/example","params":{"x":' + value + b'}}\n')
                    self.assertTrue(observer.receipt["errors"])

    def test_scalar_or_null_params_invalid_for_requests_and_notifications(self):
        for direction in ("in", "out"):
            for value in (None, True, 3, "PRIVATE-PARAM"):
                for with_id in (False, True):
                    with self.subTest(direction=direction, value=value, with_id=with_id):
                        observer = proxy.Observer()
                        message = {"method": "custom", "params": value}
                        if with_id:
                            message["id"] = 1
                        self.send(observer, direction, **message)
                        self.assertTrue(observer.receipt["errors"])
                        self.assertNotIn("PRIVATE-PARAM", json.dumps(observer.receipt))

    def test_unsolicited_and_duplicate_responses_rejected_in_each_direction(self):
        for direction in ("in", "out"):
            with self.subTest(direction=direction, case="unsolicited"):
                observer = proxy.Observer()
                self.send(observer, direction, id=1, result={})
                self.assertTrue(observer.receipt["errors"])
            with self.subTest(direction=direction, case="duplicate"):
                observer = proxy.Observer()
                opposite = "out" if direction == "in" else "in"
                self.send(observer, opposite, id=1, method="custom")
                self.send(observer, direction, id=1, result={})
                self.assertFalse(observer.receipt["errors"])
                self.send(observer, direction, id=1, result={})
                self.assertTrue(observer.receipt["errors"])

    def test_valid_bidirectional_same_id_requests_and_responses(self):
        observer = proxy.Observer()
        self.send(observer, "in", id=1, method="tools/list", params={})
        self.send(observer, "out", id=1, method="sampling/createMessage", params={})
        self.send(observer, "in", id=1, result={"secret": "PRIVATE-CONTENT"})
        self.send(observer, "out", id=1, result={"tools": [{"name": "analyze-work"}]})
        self.assertFalse(observer.receipt["errors"])
        self.assertFalse(observer.pending)
        self.assertNotIn("PRIVATE-CONTENT", json.dumps(observer.receipt))

    def test_invalid_jsonrpc_error_and_response_params_rejected(self):
        responses = [{"id": 1, "error": None}, {"id": 1, "error": {"code": True, "message": "x"}},
                     {"id": 1, "error": {"code": 1, "message": 2}},
                     {"id": 1, "result": {}, "params": {}}]
        for response in responses:
            with self.subTest(response=response):
                observer = proxy.Observer()
                self.send(observer, "in", id=1, method="custom")
                self.send(observer, "out", **response)
                self.assertTrue(observer.receipt["errors"])
                self.assertTrue(observer.pending)

    def test_duplicate_json_keys_cannot_forge_response_or_id(self):
        observer = proxy.Observer()
        self.send(observer, "in", id=1, method="tools/list")
        observer.feed("out", b'{"jsonrpc":"2.0","id":2,"id":1,"result":{"tools":[{"name":"analyze-work"}]}}\n')
        self.assertTrue(observer.pending)
        self.assertEqual(observer.receipt["listings"], [])
        self.assertTrue(observer.receipt["errors"])


class ProxyTests(unittest.TestCase):
    def test_bidirectional_process_collision_is_valid(self):
        server = r'''
import json, sys
request = json.loads(sys.stdin.readline())
print(json.dumps({"jsonrpc":"2.0", "id":request["id"], "method":"sampling/createMessage", "params":{}}), flush=True)
response = json.loads(sys.stdin.readline())
assert response["id"] == request["id"] and response["result"] == {}
print(json.dumps({"jsonrpc":"2.0", "id":request["id"], "result":{"tools":[{"name":"analyze-work"}]}}), flush=True)
'''
        with tempfile.TemporaryDirectory() as temp:
            receipt = Path(temp) / "receipt.json"
            proc = subprocess.Popen([sys.executable, str(PROXY), "--receipt", str(receipt), "--", sys.executable, "-c", server],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                proc.stdin.write(b'{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n')
                proc.stdin.flush()
                self.assertTrue(select.select([proc.stdout], [], [], 10)[0])
                self.assertEqual(json.loads(proc.stdout.readline())["method"], "sampling/createMessage")
                proc.stdin.write(b'{"jsonrpc":"2.0","id":1,"result":{}}\n')
                proc.stdin.flush()
                self.assertTrue(select.select([proc.stdout], [], [], 10)[0])
                self.assertEqual(json.loads(proc.stdout.readline())["result"]["tools"][0]["name"], "analyze-work")
                proc.stdin.close()
                self.assertEqual(proc.wait(timeout=10), 0)
                self.assertTrue(json.loads(receipt.read_text())["complete"])
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
                for stream in (proc.stdin, proc.stdout, proc.stderr):
                    if not stream.closed:
                        stream.close()

    def test_unanswered_analyze_work_call_is_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            receipt = Path(temp) / "receipt.json"
            server = "import sys; sys.stdin.buffer.read()"
            call = {"jsonrpc": "2.0", "id": 8, "method": "tools/call", "params": {"name": "analyze-work", "arguments": {"request": {"secret": "PRIVATE-REQUEST"}}}}
            result = subprocess.run([sys.executable, str(PROXY), "--receipt", str(receipt), "--", sys.executable, "-c", server],
                                    input=json.dumps(call).encode() + b"\n", capture_output=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            evidence = json.loads(receipt.read_text())
            self.assertFalse(evidence["complete"])
            self.assertIn("incomplete_message", evidence["errors"])
            self.assertNotIn("PRIVATE-REQUEST", json.dumps(evidence))

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
