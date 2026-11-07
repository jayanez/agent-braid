# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T005 (REQ-005 gate): probe each host with the nested per-kind ``analyze-work`` schema.

A recording stdio MCP server (a test double, not the product) serves the model-facing ``analyze-work``
definition of the candidate checkout (D9 arm ``per-kind`` and/or ``description-only``). For each host the
probe runs three real prompts (aim, git, units) in a disposable profile, with the driver's isolation
(``scripts/spec069_native_runs.py``: private HOME/XDG, OS sandbox, credential only from this process's
environment, redaction and secret scan), and records:

* whether the host accepted the definition (listed it, and the model called it),
* whether each call conforms to the declared schema (``request`` an object, not a string),
* the exact bytes the host received (``tools/list`` line and its canonical hash, per connection),
* for Anthropic-API hosts, the tool definition the host sent to the model API (through a local recording
  forwarder; only tool names, hashes and presence are kept, never request bodies or headers), which shows
  whether the schema was loaded eagerly or after a tool-search step.

    python -m scripts.spec069_host_probe --model claude-code=<id> --model opencode=anthropic/<id>
    python -m scripts.spec069_host_probe serve DEFINITION.json RECORD.jsonl   # the test double

A host without a credential in the environment is reported as a declared limit.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import http.server
import json
import os
import platform
import sys
import threading
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "specs/069-aim-request-authoring"
TOOL = "analyze-work"
SERVER = "probe"
WORKSPACE_ID = "probe-workspace"
PROTOCOL_FALLBACK = "2025-06-18"

PROMPTS = {
    "aim": "Use the analyze-work tool of the probe MCP server (workspaceId \"probe-workspace\") to check whether two edits can "
           "safely be worked on at the same time. One person will reword the install section of README.md. Another person will "
           "add a build-status badge line near the top of README.md. Make the tool call, then stop.",
    "git": "Use the analyze-work tool of the probe MCP server (workspaceId \"probe-workspace\") to check whether the work on the "
           "two branches docs-guide and src-api of the project repository can proceed in parallel. Both branches were cut "
           "from main. Make the tool call, then stop.",
    "units": "Use the analyze-work tool of the probe MCP server (workspaceId \"probe-workspace\") to check two units of work "
             "that declare the resources they touch: unit \"a\" writes README.md and unit \"b\" also writes README.md. "
             "Make the tool call, then stop.",
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ----------------------------------------------------------------------------
# The test double: a stdio MCP server that records every line in both directions
# ----------------------------------------------------------------------------
def serve(definition_file: str, record_file: str) -> int:
    definition = json.loads(Path(definition_file).read_text(encoding="utf-8"))
    record = open(record_file, "a", encoding="utf-8", buffering=1)

    def note(direction: str, line: str) -> None:
        record.write(json.dumps({"dir": direction, "line": line}, ensure_ascii=False) + "\n")

    def send(message: dict) -> None:
        line = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
        note("out", line)
        sys.stdout.write(line + "\n")
        sys.stdout.flush()

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        note("in", raw)
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            continue
        method, ident = message.get("method"), message.get("id")
        if ident is None:
            continue
        if method == "initialize":
            version = (message.get("params") or {}).get("protocolVersion") or PROTOCOL_FALLBACK
            send({"jsonrpc": "2.0", "id": ident, "result": {"protocolVersion": version, "capabilities": {"tools": {}},
                                                              "serverInfo": {"name": "spec069-probe", "version": "0"}}})
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": ident, "result": {"tools": [definition]}})
        elif method == "tools/call":
            send({"jsonrpc": "2.0", "id": ident, "result": {"content": [{"type": "text", "text": json.dumps(
                {"status": "ok", "summary": "probe server: call recorded, nothing analyzed"})}], "isError": False}})
        elif method == "ping":
            send({"jsonrpc": "2.0", "id": ident, "result": {}})
        else:
            send({"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": "method not found"}})
    return 0


def read_record(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []


def summarize_connection(rows: list[dict], expected_sha: str) -> dict[str, Any]:
    """Facts about one host connection from the recorded lines."""
    info: dict[str, Any] = {"initialize": None, "toolsList": [], "toolsCalls": []}
    for row in rows:
        message = json.loads(row["line"])
        if row["dir"] == "in" and message.get("method") == "initialize":
            params = message.get("params") or {}
            info["initialize"] = {"protocolVersionRequested": params.get("protocolVersion"), "clientInfo": params.get("clientInfo")}
        elif row["dir"] == "out" and "result" in message and isinstance(message["result"], dict) and "tools" in message["result"]:
            tool = message["result"]["tools"][0]
            info["toolsList"].append({"lineSha256": sha(row["line"].encode("utf-8")), "lineBytes": len(row["line"].encode("utf-8")),
                                      "toolCanonicalSha256": sha(canonical(tool)), "matchesDefinition": sha(canonical(tool)) == expected_sha})
        elif row["dir"] == "in" and message.get("method") == "tools/call":
            info["toolsCalls"].append((message.get("params") or {}))
    return info


def conformance(arguments: Any, schema: dict) -> dict[str, Any]:
    import jsonschema

    request = arguments.get("request") if isinstance(arguments, dict) else None
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(arguments), key=lambda e: list(e.absolute_path))
    return {"requestType": type(request).__name__, "requestIsObject": isinstance(request, dict), "kind": (arguments or {}).get("kind") if isinstance(arguments, dict) else None,
            "validates": not errors, "errorCount": len(errors),
            "firstErrors": [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message[:140]}" for e in errors[:3]]}


# ----------------------------------------------------------------------------
# Recording forwarder to the Anthropic API: keeps tool names and hashes only
# ----------------------------------------------------------------------------
class Forwarder:
    def __init__(self, upstream: str, input_schema_sha: str) -> None:
        self.requests: list[dict[str, Any]] = []
        self.lock = threading.Lock()
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_: Any) -> None:  # silence
                return

            def do_POST(self) -> None:  # noqa: N802
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                owner.note(body, input_schema_sha)
                conn = http.client.HTTPSConnection(upstream, timeout=600)
                headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "content-length", "accept-encoding", "connection")}
                headers["Content-Length"] = str(len(body))
                conn.request("POST", self.path, body, headers)
                reply = conn.getresponse()
                self.send_response(reply.status)
                for key, value in reply.getheaders():
                    if key.lower() not in ("transfer-encoding", "content-length", "connection", "content-encoding"):
                        self.send_header(key, value)
                self.send_header("Connection", "close")
                self.end_headers()
                while chunk := reply.read(4096):
                    self.wfile.write(chunk)
                    self.wfile.flush()
                self.close_connection = True
                conn.close()

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def note(self, body: bytes, input_schema_sha: str) -> None:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return
        tools = payload.get("tools") if isinstance(payload, dict) else None
        if not isinstance(tools, list):
            return
        entry: dict[str, Any] = {"toolNames": [t.get("name") for t in tools if isinstance(t, dict)], "analyzeWork": None}
        for tool in tools:
            if isinstance(tool, dict) and str(tool.get("name", "")).endswith(TOOL):
                schema = tool.get("input_schema") or tool.get("inputSchema") or tool.get("parameters")
                entry["analyzeWork"] = {"name": tool.get("name"), "inputSchemaSha256": sha(canonical(schema)) if schema is not None else None,
                                        "inputSchemaEqualsServed": schema is not None and sha(canonical(schema)) == input_schema_sha,
                                        "inputSchemaBytes": len(canonical(schema)) if schema is not None else 0,
                                        "hasDescription": bool(tool.get("description"))}
        with self.lock:
            self.requests.append(entry)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


# ----------------------------------------------------------------------------
# Host wiring
# ----------------------------------------------------------------------------
def host_tool_matches(host: str, name: str) -> bool:
    return {"claude-code": name == f"mcp__{SERVER}__{TOOL}", "opencode": name == f"{SERVER}_{TOOL}",
            "codex": name in (f"{SERVER}__{TOOL}", f"mcp__{SERVER}__{TOOL}", TOOL)}[host]


def definition_for(arm: str) -> dict[str, Any]:
    """The model-facing ``analyze-work`` definition of this checkout for a D9 arm (workspaceId injected like the plugin does)."""
    sys.path.insert(0, str(ROOT))
    from scripts import spec069_capture_t005_evidence as t005

    _, texts = t005.listed_sizes()
    return json.loads(texts[arm])


def configure_host(nr: Any, host: Any, env: dict[str, str], argv_server: list[str], mcp_file: Path, forwarder_url: str | None) -> None:
    if host.name == "opencode":
        nr.write_host_policy(host, env)
        path = Path(env["XDG_CONFIG_HOME"]) / "opencode" / "opencode.json"
        config = json.loads(path.read_text()) if path.exists() else {}
        config["mcp"] = {SERVER: {"type": "local", "command": argv_server, "enabled": True}}
        config["permission"] = {name: "deny" for name in nr.OPENCODE_DENIED}
        if forwarder_url:
            config["provider"] = {"anthropic": {"options": {"baseURL": forwarder_url + "/v1"}}}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config))
    elif host.name == "codex":
        config = Path(env["CODEX_HOME"]) / "config.toml"
        config.write_text(f'[mcp_servers.{SERVER}]\ncommand = {json.dumps(argv_server[0])}\nargs = {json.dumps(argv_server[1:])}\n')
    else:
        mcp_file.write_text(json.dumps({"mcpServers": {SERVER: {"command": argv_server[0], "args": argv_server[1:]}}}))


def probe_argv(nr: Any, host: Any, prompt: str, mcp_file: Path, max_turns: int) -> list[str]:
    binary = str(host.binary)
    if host.name == "claude-code":
        argv = [binary, "-p", prompt, "--output-format", "stream-json", "--verbose", "--max-turns", str(max_turns), "--no-session-persistence",
                "--mcp-config", str(mcp_file), "--strict-mcp-config", "--tools", "ToolSearch", "--allowedTools", f"mcp__{SERVER}__*", "ToolSearch",
                "--disallowedTools", *nr.CLAUDE_DENIED]
        return argv + (["--model", host.model] if host.model else [])
    if host.name == "codex":
        argv = [binary, "exec", "--json", "--skip-git-repo-check", "-s", "read-only", "-c", 'approval_policy="never"']
        return argv + (["-m", host.model] if host.model else []) + [prompt]
    argv = [binary, "run", "--standalone", "--format", "json"]
    return argv + (["-m", host.model] if host.model else []) + [prompt]


def probe_host(nr: Any, fixture: Any, host: Any, arm: str, definition: dict, ctx: dict, args: argparse.Namespace,
               profile: Any, secrets: Any, out_dir: Path) -> dict[str, Any]:
    import time

    key = next((os.environ[n] for n in nr.KEY_SPECS[host.name][0] if os.environ.get(n)), None)
    if not key:
        raise nr.DeclaredLimit(f"no {' or '.join(nr.KEY_SPECS[host.name][0])} in the environment: {host.name} was not run (declared limit)")
    if host.name == "opencode" and not host.model:
        raise nr.DeclaredLimit("OpenCode needs --model opencode=anthropic/<id>")
    secrets.add(key)
    protected, sandbox = ctx["protected"], ctx["sandbox"]
    root = profile.make("hosts", f"{host.name}-{arm}")
    env = nr.build_host_env(profile, host, key, profile.make("hosts", host.name, "agent-braid-home"), {})
    workspace = fixture.build(root / "workspace" / "repo")
    probe = nr.probe_isolation(env, Path(env["HOME"]), sandbox, protected)
    version = nr.version_of(host, env, workspace, profile, protected, sandbox)
    definition_file = root / "definition.json"
    definition_file.write_text(json.dumps(definition, ensure_ascii=False))
    expected = sha(canonical(definition))
    schema_sha = sha(canonical(definition["inputSchema"]))
    forwarder = None
    if host.name in ("claude-code", "opencode"):
        forwarder = Forwarder("api.anthropic.com", schema_sha)
        forwarder.start()
        if host.name == "claude-code":
            env["ANTHROPIC_BASE_URL"] = forwarder.url
    runs = []
    try:
        for kind, prompt in PROMPTS.items():
            record = root / f"{kind}.record.jsonl"
            argv_server = [sys.executable, "-I", str(Path(__file__).resolve()), "serve", str(definition_file), str(record)]
            mcp_file = root / "mcp.json"
            configure_host(nr, host, env, argv_server, mcp_file, forwarder.url if forwarder else None)
            seen_before = len(forwarder.requests) if forwarder else 0
            started = time.time()
            done = nr.run_process(probe_argv(nr, host, prompt, mcp_file, args.max_turns), env, workspace, profile, protected, sandbox,
                                  args.timeout, f"{host.name} probe {kind}")
            stdout, stderr = secrets.redact(done.stdout), secrets.redact(done.stderr)
            transcript = nr.PARSERS[host.name](done.stdout)
            rows = read_record(record)
            conn = summarize_connection(rows, expected)
            calls = [dict(conformance(c.get("arguments"), definition["inputSchema"]), tool=c.get("name")) for c in conn["toolsCalls"]]
            seen = (forwarder.requests[seen_before:] if forwarder else [])
            names = [c.tool for c in transcript.tool_calls]
            first_with = next((i for i, r in enumerate(seen) if r["analyzeWork"]), None)
            host_error = None
            if not transcript.tool_calls:
                tail = (stdout.strip().splitlines() or stderr.strip().splitlines() or ["no output"])[-1]
                row = next((r for r in reversed(nr._jsonl(done.stdout)) if r.get("is_error") or r.get("type") == "error"), None)
                host_error = (str((row or {}).get("result") or (row or {}).get("error") or "")[:200] or (tail[:200] if done.returncode else None))
            file = out_dir / host.name / f"{arm}-{kind}.jsonl"
            file.parent.mkdir(parents=True, exist_ok=True)
            body = stdout + "\n" + "\n".join(f"#stderr {line}" for line in stderr.splitlines()[-40:]) + "\n"
            secrets.assert_clean(file.name, body)
            file.write_text(body)
            runs.append({"prompt": kind, "exitCode": done.returncode, "timedOut": done.timed_out, "durationSeconds": round(time.time() - started, 1),
                         "transcript": {"file": str(file.relative_to(out_dir.parent)), "sha256": sha(body.encode()), "bytes": len(body.encode())},
                         "models": transcript.models, "toolNames": names, "hostError": secrets.redact(host_error) if host_error else None, "toolSearchCalledBeforeAnalyzeWork": "ToolSearch" in names,
                         "listedByHost": bool(conn["toolsList"]), "connection": {k: v for k, v in conn.items() if k != "toolsCalls"},
                         "calls": secrets.redact_json(calls), "firstCallArguments": secrets.redact_json(conn["toolsCalls"][0].get("arguments")) if conn["toolsCalls"] else None,
                         "apiRequests": secrets.redact_json({"count": len(seen), "firstRequestHadAnalyzeWork": bool(seen and seen[0]["analyzeWork"]),
                                                             "firstRequestIndexWithAnalyzeWork": first_with,
                                                             "analyzeWorkSchemaEqualsServedInEveryRequest": all(r["analyzeWork"]["inputSchemaEqualsServed"] for r in seen if r["analyzeWork"]) if any(r["analyzeWork"] for r in seen) else None,
                                                             "firstRequestToolNames": seen[0]["toolNames"] if seen else None,
                                                             "analyzeWorkEntry": next((r["analyzeWork"] for r in seen if r["analyzeWork"]), None)}) if forwarder else None})
    finally:
        if forwarder:
            forwarder.stop()
    return {"status": "ran", "version": version, "model": host.model, "arm": arm, "osSandbox": probe["sandbox"], "probe": probe,
            "expectedDefinitionCanonicalSha256": expected, "expectedInputSchemaCanonicalSha256": schema_sha,
            "expectedModelFacingBytes": len(json.dumps(definition, ensure_ascii=False, separators=(",", ":")).encode()), "runs": runs}


def verdict(result: dict) -> dict[str, Any]:
    """Per host and arm: accepted, conforming, byte identity, loading mode."""
    runs = result["runs"]
    lists = [item for r in runs for item in r["connection"]["toolsList"]]
    calls = [c for r in runs for c in r["calls"]]
    loading = None
    flags = [r["apiRequests"] for r in runs if r.get("apiRequests")]
    if flags:
        loading = "eager" if all(f["firstRequestHadAnalyzeWork"] for f in flags) else (
            "deferred" if any(f["firstRequestIndexWithAnalyzeWork"] not in (None, 0) for f in flags) or any(r["toolSearchCalledBeforeAnalyzeWork"] for r in runs) else "not-observed")
    errors = sorted({r["hostError"] for r in runs if r.get("hostError") and not r["calls"]})
    return {"modelAnswered": not errors and bool(calls), "hostErrors": errors, "hostListedTool": all(r["listedByHost"] for r in runs), "modelCalledToolInPrompts": [r["prompt"] for r in runs if r["calls"]],
            "callsMade": len(calls), "requestAlwaysObject": all(c["requestIsObject"] for c in calls) if calls else None,
            "callsConformToDeclaredSchema": f"{sum(c['validates'] for c in calls)}/{len(calls)}",
            "servedBytesEqualDefinition": all(i["matchesDefinition"] for i in lists) if lists else None,
            "toolsListSha256s": sorted({i["toolCanonicalSha256"] for i in lists}), "loading": loading}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["serve"]:
        return serve(argv[1], argv[2])
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--hosts", default="claude-code,opencode,codex")
    p.add_argument("--arms", default="per-kind", help="comma list of per-kind, description-only")
    p.add_argument("--model", action="append", default=[], metavar="HOST=ID")
    p.add_argument("--claude-bin")
    p.add_argument("--codex-bin")
    p.add_argument("--opencode-bin")
    p.add_argument("--timeout", type=int, default=240)
    p.add_argument("--max-turns", type=int, default=6)
    p.add_argument("--output", type=Path, default=SPEC_DIR / "evidence/host-probe-nested-schema.json")
    p.add_argument("--no-os-sandbox", action="store_true")
    p.add_argument("--fake-hosts", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--real-home", type=Path, default=None)
    args = p.parse_args(argv)
    sys.path.insert(0, str(ROOT))
    from scripts import spec069_fixture_workspace as fixture
    from scripts import spec069_native_runs as nr

    models = dict(item.split("=", 1) for item in args.model)
    secrets = nr.Secrets()
    home = args.real_home or nr.real_home()
    protected = nr.real_config_paths(home)
    sandbox = nr.OsSandbox(protected, enabled=not args.no_os_sandbox)
    out_dir = args.output.with_suffix(".transcripts")
    profile = nr.Profile()
    evidence: dict[str, Any] = {"evidenceVersion": 1, "task": "SPEC-069 T005 host probe of the nested per-kind schema",
                                "generatedAt": nr.utc_now(), "platform": platform.platform(), "label": "host-run",
                                "double": "scripts/spec069_host_probe.py serve (recording stdio MCP test double, not the product)",
                                "scriptSha256": sha(Path(__file__).read_bytes()), "driverSha256": nr.sha256_file(Path(nr.__file__)),
                                "prompts": PROMPTS, "results": {}}
    exit_code = 0
    try:
        ctx = {"protected": protected, "sandbox": sandbox}
        ns = argparse.Namespace(claude_bin=args.claude_bin, codex_bin=args.codex_bin, opencode_bin=args.opencode_bin, fake_hosts=args.fake_hosts)
        for arm in [a for a in args.arms.split(",") if a]:
            definition = definition_for(arm)
            evidence.setdefault("definitions", {})[arm] = {"canonicalSha256": sha(canonical(definition)), "inputSchemaCanonicalSha256": sha(canonical(definition["inputSchema"])),
                                                           "bytes": len(json.dumps(definition, ensure_ascii=False, separators=(",", ":")).encode())}
            for name in [h for h in args.hosts.split(",") if h]:
                key = f"{name}/{arm}"
                binary = nr.host_binary(name, ns)
                if binary is None:
                    evidence["results"][key] = {"status": "declared-limit", "limit": f"{name} executable not found"}
                    continue
                host = nr.HostConfig(name, binary, *nr.KEY_SPECS[name], model=models.get(name), fake=args.fake_hosts)
                try:
                    result = probe_host(nr, fixture, host, arm, definition, ctx, args, profile, secrets, out_dir)
                    result["verdict"] = verdict(result)
                    evidence["results"][key] = result
                except nr.DeclaredLimit as limit:
                    evidence["results"][key] = {"status": "declared-limit", "limit": secrets.redact(str(limit))}
    except nr.SafetyStop as stop:
        evidence["stopped"] = secrets.redact(str(stop))
        exit_code = nr.EXIT_SAFETY
    except nr.SecretLeak as leak:
        evidence["stopped"] = str(leak)
        exit_code = nr.EXIT_SECRET
    finally:
        evidence["teardown"] = profile.teardown()
    if not evidence["teardown"]["clean"]:
        exit_code = exit_code or nr.EXIT_TEARDOWN
    try:
        nr.write_evidence(args.output, evidence, secrets)
    except nr.SecretLeak as leak:
        print(f"refusing to write evidence: {leak}", file=sys.stderr)
        return nr.EXIT_SECRET
    print(json.dumps({"evidence": str(args.output), "exit": exit_code, "stopped": evidence.get("stopped"), "teardown": evidence["teardown"],
                      "hosts": {k: (v.get("verdict") or v.get("limit") or v.get("status")) for k, v in evidence["results"].items()}}, indent=1))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
