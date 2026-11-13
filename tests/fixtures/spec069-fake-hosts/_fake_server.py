# SPDX-License-Identifier: AGPL-3.0-only
"""Fake ``launch plugin serve`` for the ``--probe-schema`` self-test: a minimal newline-delimited MCP server.

It lists the ``analyze-work`` definition the driver wrote next to it (``definition.json``) and answers every call with an
``ok`` envelope. It answers ``plugin setup`` like the plain fake launcher. Not the product.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
if args[:2] == ["plugin", "setup"]:
    print(json.dumps({"previewDigest": "f" * 64, "registry": {"workspaces": [{"workspaceId": "fake-workspace-0001"}]}}))
    sys.exit(0)
if args[:2] != ["plugin", "serve"]:
    print("{}")
    sys.exit(0)
with open(os.path.join(HERE, "definition.json"), encoding="utf-8") as handle:
    definition = json.load(handle)
tools = [definition, {"name": "workspaces", "description": "List workspaces.", "inputSchema": {"type": "object"}}]
for line in sys.stdin:
    message = json.loads(line)
    if "id" not in message:
        continue
    method = message.get("method")
    if method == "initialize":
        result = {"protocolVersion": message["params"]["protocolVersion"], "capabilities": {"tools": {}},
                  "serverInfo": {"name": "agent-braid-fake", "version": "0.0.0-fake"}}
    elif method == "tools/list":
        result = {"tools": tools}
    elif method == "tools/call":
        text = json.dumps({"operation": message["params"]["name"], "status": "ok", "summary": "ok"})
        result = {"content": [{"type": "text", "text": text}], "isError": False}
    else:
        result = {}
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}) + "\n")
    sys.stdout.flush()
