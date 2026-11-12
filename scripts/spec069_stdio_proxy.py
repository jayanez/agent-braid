# SPDX-License-Identifier: AGPL-3.0-only
"""Offline-capable MCP stdio relay. One invocation and receipt per connection.

Only hashes and bounded, allowlisted metadata are persisted; never store traffic.
The receipt is not evidence of host acceptance or model-side schema loading.
"""

import argparse
import hashlib
import json
import math
import os
import re
import selectors
import signal
import subprocess
import sys
import time

MAX_LINE = 1024 * 1024
MAX_EVENTS = 4096


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("non-JSON numeric constant")


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("number outside finite float range")
    return number


class Observer:
    def __init__(self):
        self.pending = {}
        self.server_pending = {}
        self.buffers = {"in": b"", "out": b""}
        self.receipt = {"version": 1, "complete": False, "protocolVersion": None, "listings": [], "calls": [], "errors": []}

    def fail(self, code):
        if code not in self.receipt["errors"]:
            self.receipt["errors"].append(code)

    def feed(self, direction, data):
        buf = self.buffers[direction] + data
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            if len(line) > MAX_LINE:
                self.fail("line_limit")
                raise ValueError("MCP line limit exceeded")
            else:
                self.line(direction, line + b"\n")
        if len(buf) > MAX_LINE:
            self.fail("line_limit")
            raise ValueError("MCP line limit exceeded")
        self.buffers[direction] = buf

    def line(self, direction, raw):
        try:
            msg = json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant, parse_float=finite_float)
            if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
                raise ValueError
            ident = msg.get("id")
            if "id" in msg and (isinstance(ident, bool) or not isinstance(ident, (str, int))):
                raise ValueError
            if isinstance(ident, str) and len(ident) > 128:
                raise ValueError
            key = (type(ident).__name__, ident)
            if "method" in msg:
                method = msg["method"]
                if not isinstance(method, str) or "result" in msg or "error" in msg:
                    raise ValueError
                if "params" in msg and not isinstance(msg["params"], (dict, list)):
                    raise ValueError
                if direction == "in" and method in ("initialize", "tools/list", "tools/call") and "id" not in msg:
                    raise ValueError
                if direction == "in" and method == "initialize":
                    params = msg.get("params")
                    offered_version = params.get("protocolVersion") if isinstance(params, dict) else None
                    if not isinstance(offered_version, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", offered_version):
                        raise ValueError
                if "id" in msg:
                    pending = self.pending if direction == "in" else self.server_pending
                    if key in pending or len(pending) >= MAX_EVENTS:
                        raise ValueError
                    pending[key] = method
                if direction == "in" and method == "tools/call" and isinstance(msg.get("params"), dict) and msg["params"].get("name") == "analyze-work":
                    params = msg.get("params")
                    args = params.get("arguments") if isinstance(params, dict) else None
                    request = args.get("request") if isinstance(args, dict) else None
                    request_type = "object" if isinstance(request, dict) else "array" if isinstance(request, list) else "other"
                    if len(self.receipt["calls"]) >= MAX_EVENTS:
                        raise ValueError
                    self.receipt["calls"].append({"requestType": request_type})
            else:
                if "id" not in msg or "params" in msg or ("result" in msg) == ("error" in msg):
                    raise ValueError
                if "error" in msg:
                    error = msg["error"]
                    if (not isinstance(error, dict) or isinstance(error.get("code"), bool)
                            or not isinstance(error.get("code"), int) or not isinstance(error.get("message"), str)):
                        raise ValueError
                pending = self.pending if direction == "out" else self.server_pending
                if key not in pending:
                    raise ValueError
                method = pending.pop(key)
                if direction != "out":
                    return
                if method not in ("initialize", "tools/list", "tools/call"):
                    return
                result = msg.get("result")
                if not isinstance(result, dict):
                    self.fail("rpc_error")
                elif method == "initialize":
                    version = result.get("protocolVersion")
                    if not isinstance(version, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", version):
                        raise ValueError
                    self.receipt["protocolVersion"] = version
                elif method == "tools/list":
                    tools = result.get("tools")
                    if not isinstance(tools, list) or len(tools) > MAX_EVENTS:
                        raise ValueError
                    target = [tool for tool in tools if isinstance(tool, dict) and tool.get("name") == "analyze-work"]
                    if len(target) != 1 or len(self.receipt["listings"]) >= MAX_EVENTS:
                        raise ValueError
                    self.receipt["listings"].append({"lineSha256": digest(raw), "lineBytes": len(raw),
                        "resultCanonicalSha256": digest(canonical(result)),
                        "analyzeWorkCanonicalSha256": digest(canonical(target[0])),
                        "toolCount": len(tools)})
        except (ValueError, TypeError, UnicodeError, RecursionError):
            self.fail("invalid_or_excess_message")


def relay(command, receipt):
    observer = Observer()
    child = None
    status = 1
    def interrupted(signum, frame):
        raise InterruptedError
    old = {sig: signal.signal(sig, interrupted) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, start_new_session=True)
        with selectors.DefaultSelector() as selector:
            selector.register(sys.stdin.buffer, selectors.EVENT_READ, ("in", child.stdin))
            selector.register(child.stdout, selectors.EVENT_READ, ("out", sys.stdout.buffer))
            deadline = None
            while selector.get_map():
                timeout = None if deadline is None else max(0, deadline - time.monotonic())
                events = selector.select(timeout)
                if not events:
                    raise subprocess.TimeoutExpired(command, 5)
                for event, _ in events:
                    direction, dest = event.data
                    data = os.read(event.fileobj.fileno(), 65536)
                    if not data:
                        selector.unregister(event.fileobj)
                        if direction == "in":
                            child.stdin.close()
                            deadline = time.monotonic() + 5
                        else:
                            # The server is gone; do not wait forever for a client to close.
                            if sys.stdin.buffer in selector.get_map():
                                selector.unregister(sys.stdin.buffer)
                                child.stdin.close()
                                observer.fail("server_closed_early")
                        continue
                    observer.feed(direction, data)
                    dest.write(data)
                    dest.flush()
        status = child.wait(timeout=5)
    except (OSError, ValueError, InterruptedError, subprocess.TimeoutExpired):
        observer.fail("relay_failure")
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        if child is not None:
            for stream in (child.stdin, child.stdout):
                if stream and not stream.closed:
                    stream.close()
        for sig, handler in old.items():
            signal.signal(sig, handler)
        if any(observer.buffers.values()) or observer.pending or observer.server_pending:
            observer.fail("incomplete_message")
        if status == 0 and observer.receipt["protocolVersion"] is None:
            observer.fail("missing_initialize")
        if status == 0 and not observer.receipt["listings"]:
            observer.fail("missing_target_listing")
        observer.receipt["complete"] = (
            status == 0
            and observer.receipt["protocolVersion"] is not None
            and bool(observer.receipt["listings"])
            and not observer.receipt["errors"]
        )
        json.dump(observer.receipt, receipt, sort_keys=True)
        receipt.write("\n")
        receipt.flush()
    return 0 if observer.receipt["complete"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a server command is required after --")
    fd = os.open(args.receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as receipt:
        return relay(command, receipt)


if __name__ == "__main__":
    sys.exit(main())
