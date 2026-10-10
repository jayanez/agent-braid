# SPDX-License-Identifier: AGPL-3.0-only
"""Verify a frozen Agent Braid wheel in private offline CPython installs.

No candidate is built. Installation is refused unless --execute-installed is
explicitly supplied. Child output is bounded. Raw command and protocol traces
are retained only inside the private work directory; CLI output is sanitized.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import time
import zipfile
from typing import Any

TARGETS = {
    "macos-arm64": {"sysPlatform": "darwin", "machine": "arm64", "python": "3.13.11"},
    "linux-amd64": {"sysPlatform": "linux", "machine": "x86_64", "python": "3.13.11"},
}
MAX_OUTPUT_BYTES = 1024 * 1024
MAX_COMMAND_SECONDS = 90


class ProbeError(RuntimeError):
    """Fixed, non-sensitive verification failure."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def save_receipt(work: Path, receipt: dict[str, Any]) -> None:
    path = work / "receipt.json"
    temporary = work / "receipt.json.tmp"
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(receipt, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def record_command(receipt: dict[str, Any], work: Path, name: str,
                   result: "CommandResult", *, parent_exit: int | None = None) -> None:
    if not re.fullmatch(r"[a-z0-9-]+", name):
        raise ProbeError("unsafe command trace name")
    traces = work / "commands"
    traces.mkdir(mode=0o700, exist_ok=True)
    index = len(receipt["commands"])
    prefix = traces / f"{index:02d}-{name}"
    raw_paths = {}
    for suffix, data in (("stdout", result.stdout), ("stderr", result.stderr)):
        path = prefix.with_suffix(f".{suffix}.raw")
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        raw_paths[f"raw{suffix.title()}Path"] = str(path.relative_to(work))
    row = {"name": name, **result.receipt(), **raw_paths}
    if parent_exit is not None:
        row["parentExitCode"] = parent_exit
    receipt["commands"].append(row)
    save_receipt(work, receipt)


def attach_relay_observations(work: Path, receipt: dict[str, Any]) -> None:
    rows = {}
    for mode in ("auto", "legacy"):
        status_path = work / f"{mode}-server-exit.json"
        if status_path.is_file() and not status_path.is_symlink():
            try:
                rows[mode] = parse_json_bytes(status_path.read_bytes())
            except (OSError, ProbeError):
                rows[mode] = {"status": "unavailable"}
    if rows:
        receipt["relayChildren"] = rows
        save_receipt(work, receipt)


def mark_blocked_receipt(work: Path, reason: str) -> None:
    path = work / "receipt.json"
    if not work.is_dir() or work.is_symlink() or not path.is_file() or path.is_symlink():
        return
    receipt = parse_json_bytes(path.read_bytes())
    attach_relay_observations(work, receipt)
    receipt["status"] = "blocked"
    receipt["blockedReason"] = reason
    save_receipt(work, receipt)


def parse_json_bytes(raw: bytes) -> dict[str, Any]:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=pairs,
                           parse_constant=lambda _v: (_ for _ in ()).throw(ValueError("constant")))
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProbeError("invalid bounded JSON") from exc
    if not isinstance(value, dict):
        raise ProbeError("JSON root must be an object")
    return value


def validate_target(target: str) -> None:
    expected = TARGETS[target]
    machine = os.uname().machine.lower()
    if machine == "aarch64":
        machine = "arm64"
    if (sys.version.split()[0] != expected["python"] or sys.implementation.name != "cpython"
            or sys.platform != expected["sysPlatform"] or machine != expected["machine"]):
        raise ProbeError("running interpreter does not match the selected target")


def verify_lock_and_wheelhouse(manifest_path: Path, wheelhouse: Path, target: str) -> dict[str, Any]:
    try:
        manifest_raw = manifest_path.read_bytes()
        if len(manifest_raw) > 4 * 1024 * 1024:
            raise ProbeError("manifest exceeds size bound")
        manifest = parse_json_bytes(manifest_raw)
    except OSError as exc:
        raise ProbeError("manifest is unavailable") from exc
    if manifest.get("schema") != "agent-braid-mcp-closure/v1":
        raise ProbeError("unsupported dependency manifest")
    target_row = manifest.get("target")
    if not isinstance(target_row, dict) or target_row.get("name") != target:
        raise ProbeError("dependency target mismatch")
    if target_row.get("python") != "3.13.11" or target_row.get("implementation") != "CPython":
        raise ProbeError("dependency interpreter mismatch")
    if manifest.get("directRequirements") != ["mcp==2.3.0"]:
        raise ProbeError("SDK requirement mismatch")
    lock = manifest.get("lockFile")
    if not isinstance(lock, dict) or not isinstance(lock.get("path"), str):
        raise ProbeError("lock reference is missing")
    lock_path = (manifest_path.parent / lock["path"]).resolve()
    if lock_path.parent != manifest_path.parent.resolve() or not lock_path.is_file():
        raise ProbeError("lock path is unsafe or missing")
    lock_digest = sha256_file(lock_path)
    if lock_digest != lock.get("sha256"):
        raise ProbeError("lock digest mismatch")

    package_rows = manifest.get("packages")
    if not isinstance(package_rows, list) or not package_rows:
        raise ProbeError("dependency closure is missing")
    expected = {}
    for row in package_rows:
        if not isinstance(row, dict):
            raise ProbeError("invalid package record")
        name, filename, digest = (row.get(key) for key in ("canonicalName", "wheel", "wheelSha256"))
        if (not isinstance(name, str) or name in expected or not isinstance(filename, str)
                or Path(filename).name != filename or not isinstance(digest, str) or len(digest) != 64):
            raise ProbeError("invalid package identity")
        expected[name] = row
    if not wheelhouse.is_dir() or wheelhouse.is_symlink():
        raise ProbeError("offline wheelhouse unavailable")
    wheels = sorted(wheelhouse.glob("*.whl"))
    if len(wheels) != len(expected) or {p.name for p in wheels} != {r["wheel"] for r in expected.values()}:
        raise ProbeError("wheelhouse roster mismatch")
    digests = {}
    for path in wheels:
        digest = sha256_file(path)
        row = next((item for item in expected.values() if item["wheel"] == path.name), None)
        if row is None or row["wheelSha256"] != digest:
            raise ProbeError("wheelhouse digest mismatch")
        try:
            from email.parser import Parser
            with zipfile.ZipFile(path) as archive:
                metadata_names = [name for name in archive.namelist()
                                  if name.endswith(".dist-info/METADATA")]
                if len(metadata_names) != 1:
                    raise ProbeError("dependency wheel metadata roster mismatch")
                metadata = Parser().parsestr(archive.read(metadata_names[0]).decode("utf-8"))
        except (OSError, UnicodeError, KeyError, zipfile.BadZipFile) as exc:
            raise ProbeError("dependency wheel metadata unreadable") from exc
        normalized_name = metadata.get("Name", "").lower().replace("_", "-").replace(".", "-")
        expected_name = row["canonicalName"]
        if (normalized_name != expected_name or metadata.get("Version") != row["version"]
                or metadata.get("License-Expression") != row.get("licenseExpression")
                or metadata.get("License") != row.get("licenseMetadata")
                or metadata.get_all("Requires-Dist", []) != row.get("requiresDist")):
            raise ProbeError("dependency wheel metadata differs from lock manifest")
        digests[path.name] = digest
    evaluations = manifest.get("requirementEvaluations")
    if not isinstance(evaluations, dict):
        raise ProbeError("target marker evaluation record is missing")
    edges = manifest.get("dependencyEdges")
    if not isinstance(edges, list):
        raise ProbeError("dependency graph missing")
    graph = {name: set() for name in expected}
    active_edges = set()
    for edge in edges:
        if (not isinstance(edge, dict) or edge.get("from") not in expected
                or edge.get("to") not in expected or not isinstance(edge.get("requirement"), str)):
            raise ProbeError("invalid dependency edge")
        graph[edge["from"]].add(edge["to"])
        active_edges.add((edge["from"], edge.get("fromExtra"), edge["to"], edge["requirement"],
                          tuple(edge.get("requestedExtras", []))))
    recorded_edges = set()
    requirement_pattern = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[([^\]]+)\])?")
    marker_env = manifest.get("markerEnvironment")
    if not isinstance(marker_env, dict) or marker_env.get("python_full_version") != "3.13.11":
        raise ProbeError("target marker environment is missing")
    for name, package in expected.items():
        contexts = {None, *package.get("requestedExtras", [])}
        for context in contexts:
            key = f"{name}|{context or ''}"
            rows = evaluations.get(key)
            if not isinstance(rows, list) or len(rows) != len(package.get("requiresDist", [])):
                raise ProbeError("conditional requirement evaluations are incomplete")
            for raw_requirement, evaluated in zip(package["requiresDist"], rows):
                if (not isinstance(evaluated, dict) or evaluated.get("requirement") != raw_requirement
                        or evaluated.get("markerContext") != context
                        or not isinstance(evaluated.get("markerMatched"), bool)):
                    raise ProbeError("conditional requirement evaluation differs from wheel metadata")
                match = requirement_pattern.match(raw_requirement)
                if match is None:
                    raise ProbeError("unsupported requirement syntax in dependency manifest")
                destination = match.group(1).lower().replace("_", "-").replace(".", "-")
                requested = tuple(sorted(item.strip().lower().replace("_", "-").replace(".", "-")
                                         for item in (match.group(2) or "").split(",") if item.strip()))
                if evaluated["markerMatched"]:
                    if (evaluated.get("selectedPackage") != destination
                            or tuple(evaluated.get("requestedExtras", [])) != requested):
                        raise ProbeError("active marker evaluation target mismatch")
                    recorded_edges.add((name, context, destination, raw_requirement, requested))
                elif evaluated.get("selectedPackage") is not None or evaluated.get("requestedExtras") != []:
                    raise ProbeError("inactive marker evaluation incorrectly selects a dependency")
    if active_edges != recorded_edges:
        raise ProbeError("marker evaluations and resolved dependency edges disagree")
    reached, pending = set(), ["mcp"]
    while pending:
        node = pending.pop()
        if node in reached:
            continue
        reached.add(node)
        pending.extend(graph[node] - reached)
    if reached != set(expected):
        raise ProbeError("dependency graph is not a complete closure")
    return {
        "manifestSha256": sha256_file(manifest_path),
        "lockSha256": lock_digest,
        "packageCount": len(expected),
        "wheelCount": len(digests),
        "wheelhouseSha256": hashlib.sha256("\n".join(
            f"{name}:{digests[name]}" for name in sorted(digests)).encode()).hexdigest(),
    }


class CommandResult:
    def __init__(self, code, timed_out, output_limited, stdout, stderr, *, argv=(), cwd="",
                 elapsed_seconds=0.0, timeout_seconds=0.0, stdout_observed=None, stderr_observed=None):
        self.returncode = code
        self.timed_out = timed_out
        self.output_limited = output_limited
        self.stdout = stdout
        self.stderr = stderr
        self.argv = list(argv)
        self.cwd = str(cwd)
        self.elapsed_seconds = elapsed_seconds
        self.timeout_seconds = timeout_seconds
        self.stdout_observed = len(stdout) if stdout_observed is None else stdout_observed
        self.stderr_observed = len(stderr) if stderr_observed is None else stderr_observed

    def receipt(self):
        return {
            "returnCode": self.returncode,
            "timedOut": self.timed_out,
            "outputLimited": self.output_limited,
            "stdoutBytes": len(self.stdout),
            "stderrBytes": len(self.stderr),
            "stdoutObservedBytes": self.stdout_observed,
            "stderrObservedBytes": self.stderr_observed,
            "stdoutSha256": hashlib.sha256(self.stdout).hexdigest(),
            "stderrSha256": hashlib.sha256(self.stderr).hexdigest(),
            "outputCaptureComplete": not self.output_limited,
            "argv": self.argv,
            "cwd": self.cwd,
            "elapsedSeconds": round(self.elapsed_seconds, 6),
            "timeoutSeconds": self.timeout_seconds,
            "maxOutputBytes": MAX_OUTPUT_BYTES,
        }


def run_bounded(argv: list[str], *, cwd: Path, env: dict[str, str], timeout: float) -> CommandResult:
    if not argv or timeout <= 0 or timeout > MAX_COMMAND_SECONDS:
        raise ProbeError("invalid bounded child command")
    started = time.monotonic()
    process = subprocess.Popen(argv, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True, close_fds=True)
    assert process.stdout is not None and process.stderr is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    streams = {"stdout": bytearray(), "stderr": bytearray()}
    observed = {"stdout": 0, "stderr": 0}
    timed_out = output_limited = False
    deadline = time.monotonic() + timeout
    try:
        while selector.get_map() or process.poll() is None:
            if time.monotonic() >= deadline:
                timed_out = True
                break
            for key, _ in selector.select(0.1):
                block = os.read(key.fileobj.fileno(), 65536)
                if not block:
                    selector.unregister(key.fileobj)
                    continue
                observed[key.data] += len(block)
                remaining = MAX_OUTPUT_BYTES - len(streams["stdout"]) - len(streams["stderr"])
                streams[key.data].extend(block[:max(remaining, 0)])
                if len(block) > remaining:
                    output_limited = True
                    break
            if output_limited:
                break
    finally:
        if process.poll() is None and (timed_out or output_limited):
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=2)
        if process.poll() is None:
            process.wait(timeout=2)
        selector.close()
        process.stdout.close()
        process.stderr.close()
    return CommandResult(process.returncode, timed_out, output_limited,
                         bytes(streams["stdout"]), bytes(streams["stderr"]), argv=argv,
                         cwd=cwd, elapsed_seconds=time.monotonic() - started,
                         timeout_seconds=timeout, stdout_observed=observed["stdout"],
                         stderr_observed=observed["stderr"])


def safe_environment(binary: Path, home: Path, temporary: Path) -> dict[str, str]:
    path = [str(binary)] + [str(item) for item in (Path("/usr/bin"), Path("/bin")) if item.is_dir()]
    return {
        "PATH": os.pathsep.join(path), "HOME": str(home), "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8", "TMPDIR": str(temporary), "PYTHONNOUSERSITE": "1",
        "PIP_CONFIG_FILE": os.devnull, "PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    }


def candidate_metadata(path: Path, expected_sha: str) -> dict[str, str]:
    if path.is_symlink() or not path.is_file() or path.suffix != ".whl":
        raise ProbeError("candidate must be a regular wheel file")
    digest = sha256_file(path)
    if digest != expected_sha:
        raise ProbeError("candidate wheel digest mismatch")
    try:
        from email.parser import Parser
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
            if len(names) != 1:
                raise ProbeError("candidate metadata roster invalid")
            metadata = Parser().parsestr(archive.read(names[0]).decode("utf-8"))
    except (OSError, UnicodeError, KeyError, zipfile.BadZipFile) as exc:
        raise ProbeError("candidate metadata unreadable") from exc
    if (metadata.get("Name", "").lower().replace("_", "-") != "agent-braid"
            or metadata.get("Version") != "0.1.0a1"):
        raise ProbeError("candidate distribution identity mismatch")
    extras = {item.lower() for item in metadata.get_all("Provides-Extra", [])}
    optional_sdk = any(re.match(r"\s*mcp\s*==\s*2\.3\.0\b", item, re.I)
                       and "extra" in item.lower() and "tooling" in item.lower()
                       for item in metadata.get_all("Requires-Dist", []))
    if "tooling" not in extras or not optional_sdk:
        raise ProbeError("candidate metadata does not declare the pinned optional tooling extra")
    return {"sha256": digest, "distribution": metadata["Name"], "version": metadata["Version"]}


def candidate_resource_hashes(path: Path) -> dict[str, str]:
    prefix = "agent_braid/tooling_assets/"
    try:
        with zipfile.ZipFile(path) as archive:
            rows = {name[len(prefix):]: hashlib.sha256(archive.read(name)).hexdigest()
                    for name in archive.namelist() if name.startswith(prefix) and not name.endswith("/")}
    except (OSError, zipfile.BadZipFile, KeyError) as exc:
        raise ProbeError("candidate resources unreadable") from exc
    skills = {f"skills/agent-braid-{name}/SKILL.md"
              for name in ("analyze", "plan", "execute", "recover", "evidence")}
    expected = skills | {"hosts.json", "fixtures/fixture-inventory.json", "fixtures/prompts.json",
                         "licenses/AGPL-3.0-only.txt", "licenses/CC-BY-SA-4.0.txt",
                         "NOTICE", "TRADEMARKS.md"}
    if set(rows) != expected:
        raise ProbeError("candidate wheel does not contain twelve tooling resources")
    return rows


def _installed_audit_code(expected: dict[str, str]) -> str:
    payload = json.dumps(expected, sort_keys=True, separators=(",", ":"))
    return r'''import hashlib,importlib,importlib.metadata,importlib.resources,json,pathlib,sys
expected=json.loads(%r)
dist=importlib.metadata.distribution("agent-braid")
module=importlib.import_module("agent_braid")
origin=pathlib.Path(module.__file__).resolve(); prefix=pathlib.Path(sys.prefix).resolve()
if not origin.is_relative_to(prefix): raise SystemExit(31)
if any("agent_braid" in p and "site-packages" not in p and "dist-packages" not in p for p in sys.path): raise SystemExit(32)
actual={}
def visit(node,base=""):
    for child in node.iterdir():
        name=base+child.name
        if child.is_dir(): visit(child,name+"/")
        else: actual[name]=hashlib.sha256(child.read_bytes()).hexdigest()
visit(importlib.resources.files("agent_braid").joinpath("tooling_assets"))
if actual!=expected: raise SystemExit(33)
from agent_braid.tooling_assets import load_skill_bundle
from agent_braid.tooling_fixtures import load_inventory,fixture_input
from agent_braid.tooling_install import asset_provenance
bundle=load_skill_bundle(); inventory=load_inventory(); provenance=asset_provenance()
if len(bundle.skills)!=5 or len(inventory.fixtures)!=18 or len(inventory.prompts)!=6: raise SystemExit(34)
fixture=next(row for row in inventory.fixtures if row.definition.get("kind")=="aim")
value={"origin":str(origin),"version":dist.version,"assetCount":len(actual),
"assetRosterSha256":hashlib.sha256(json.dumps(actual,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
"skillCount":len(bundle.skills),"skillBundleSha256":bundle.sha256,"skills":bundle.inventory()["skills"],"fixtureCount":len(inventory.fixtures),
"promptCount":len(inventory.prompts),"hostMetadataSha256":provenance["hostMetadataSha256"],
"licenseFiles":provenance["licenseFiles"],"aimFixtureId":fixture.fixture_id,
"aimRequest":fixture_input(inventory,fixture.fixture_id).request}
print(json.dumps(value,sort_keys=True,separators=(",",":")))
''' % payload


def _relay_source() -> str:
    return r'''import hashlib,json,os,selectors,signal,subprocess,sys,threading
cfg=json.load(open(sys.argv[1],encoding="utf-8")); child=None; interrupted=False; forced=None
states={name:{"bytes":0,"digest":hashlib.sha256(),"retained":0,"truncated":False} for name in ("client-to-server","server-to-client","server-stderr")}
CAP=1024*1024
def save(name,data):
    state=states[name]; state["bytes"]+=len(data); state["digest"].update(data)
    limit=65536 if name=="server-stderr" else CAP
    if state["retained"]<limit:
        part=data[:limit-state["retained"]]
        if part:
            handles[name].write(part); state["retained"]+=len(part)
    if state["bytes"]>limit: state["truncated"]=True
    return state["bytes"]<=limit
handles={}
for name,path in cfg["traces"].items():
    handles[name]=open(path,"wb"); os.chmod(path,0o600)
def terminate(_sig,_frame):
    global interrupted,forced
    interrupted=True; forced="signal"
    if child is not None and child.poll() is None:
        try: os.killpg(child.pid,signal.SIGTERM)
        except ProcessLookupError: pass
for sig in (signal.SIGTERM,signal.SIGINT): signal.signal(sig,terminate)
child=subprocess.Popen(cfg["argv"],cwd=cfg["cwd"],env=cfg["env"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,close_fds=True)
def drain_stderr():
    while True:
        block=child.stderr.read(65536)
        if not block: break
        save("server-stderr",block)
thread=threading.Thread(target=drain_stderr,daemon=True); thread.start()
selector=selectors.DefaultSelector(); selector.register(sys.stdin.buffer,selectors.EVENT_READ,"in"); selector.register(child.stdout,selectors.EVENT_READ,"out")
try:
    while selector.get_map() and not interrupted and forced is None:
        for key,_ in selector.select(.1):
            data=os.read(key.fileobj.fileno(),65536)
            if key.data=="in":
                if not data:
                    selector.unregister(key.fileobj)
                    try: child.stdin.close()
                    except OSError: pass
                else:
                    if not save("client-to-server",data): forced="trace-cap"
                    try: child.stdin.write(data); child.stdin.flush()
                    except (BrokenPipeError,OSError): selector.unregister(key.fileobj)
            elif data:
                if not save("server-to-client",data): forced="trace-cap"
                sys.stdout.buffer.write(data); sys.stdout.buffer.flush()
            else: selector.unregister(key.fileobj)
finally:
    selector.close()
    if child.poll() is None:
        try: child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            forced=forced or "term"
            try: os.killpg(child.pid,signal.SIGTERM)
            except ProcessLookupError: pass
            try: child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                forced="kill"
                try: os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                child.wait(timeout=2)
    thread.join(timeout=1)
    for handle in handles.values(): handle.flush(); os.fsync(handle.fileno()); handle.close()
    trace={name:{"byteCount":state["bytes"],"sha256":state["digest"].hexdigest(),"retainedBytes":state["retained"],"truncated":state["truncated"]} for name,state in states.items()}
    value={"returnCode":child.returncode,"interrupted":interrupted,"forcedTermination":forced,"reaped":child.poll() is not None,"trace":trace}
    temporary=cfg["status"]+".tmp"
    with open(temporary,"w",encoding="utf-8") as stream:
        json.dump(value,stream,sort_keys=True); stream.flush(); os.fsync(stream.fileno())
    os.chmod(temporary,0o600); os.replace(temporary,cfg["status"])
'''


def _sdk_probe_code(relay: Path, config: Path, source: Path, results: Path,
                    home: Path, env: dict[str, str], request: dict[str, Any]) -> str:
    cfg = {"relay": str(relay), "config": str(config), "source": str(source),
           "results": str(results), "home": str(home), "path": env["PATH"], "request": request,
           "traceRoot": str(config.parent), "traceNames": {
               "client-to-server": "client-to-server.frames",
               "server-to-client": "server-to-client.frames",
               "server-stderr": "server.stderr.log"}}
    return r'''import asyncio,hashlib,json,pathlib,sys
from mcp import Client
from mcp.client.stdio import StdioServerParameters
cfg=json.loads(%r); outcomes=[]
async def one(mode):
    status=pathlib.Path(cfg["config"]).parent/(mode+"-server-exit.json")
    params=StdioServerParameters(command=sys.executable,args=["-I",cfg["relay"],cfg["config"]],
        cwd=cfg["home"],env={"HOME":cfg["home"],"PATH":cfg["path"],"PYTHONNOUSERSITE":"1"})
    base=json.loads(pathlib.Path(cfg["config"]).read_text())
    base["status"]=str(status); pathlib.Path(cfg["config"]).write_text(json.dumps(base))
    trace_paths={name:str(pathlib.Path(cfg["traceRoot"])/(mode+"-"+filename)) for name,filename in cfg["traceNames"].items()}
    base["traces"]=trace_paths; pathlib.Path(cfg["config"]).write_text(json.dumps(base))
    async with Client(params,mode=mode) as client:
        protocol=client.protocol_version
        expected_protocol="2026-07-28" if mode=="auto" else "2025-11-25"
        if protocol!=expected_protocol: raise RuntimeError("protocol version")
        tools=await client.list_tools(); names=sorted(row.name for row in tools.tools)
        if names!=["analyze","analyze-work","prepare"]: raise RuntimeError("tool roster")
        good=await client.call_tool("analyze-work",{"kind":"aim","request":cfg["request"]})
        envelope=good.structured_content
        if envelope["status"]!="ok" or envelope["result"].get("report") is None: raise RuntimeError("AIM positive")
        if json.loads(good.content[0].text)!=envelope or envelope["result"]["provenance"].get("executionAuthorization") is not False: raise RuntimeError("AIM boundary")
        bad=await client.call_tool("analyze-work",{"kind":"aim","request":{}})
        if bad.structured_content["status"]!="refused" or bad.is_error is not True: raise RuntimeError("AIM negative")
        listed=await client.list_resources()
        if "agent-braid://capabilities" not in {row.uri for row in listed.resources}: raise RuntimeError("resource roster")
        capability=await client.read_resource("agent-braid://capabilities")
        if "analysis-only" not in capability.contents[0].text: raise RuntimeError("capability resource")
        prompts=await client.list_prompts(); prompt_names=sorted(row.name for row in prompts.prompts)
        if prompt_names!=["agent-braid-analyze","agent-braid-evidence","agent-braid-plan"]: raise RuntimeError("prompt roster")
        prompt=await client.get_prompt("agent-braid-evidence")
        if "SHA-256" not in prompt.messages[0].content.text: raise RuntimeError("prompt content")
    child=json.loads(status.read_text())
    if child.get("returnCode")!=0 or child.get("interrupted") or child.get("forcedTermination") is not None or not child.get("reaped"): raise RuntimeError("server child exit")
    report=envelope["result"]["report"]
    report_digest=hashlib.sha256(json.dumps(report,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")).hexdigest()
    outcomes.append({"mode":mode,"protocolVersion":protocol,"toolCount":len(names),
        "positiveAIM":"ok","negativeAIM":"refused","capabilityResource":"read",
        "promptCount":len(prompt_names),"selectedPrompt":"read",
        "aimReportSha256":report_digest,
        "serverChildReturnCode":child["returnCode"],"serverChildReaped":child["reaped"],
        "serverChildCancelled":child["interrupted"],"serverChildForcedTermination":child["forcedTermination"],
        "serverTrace":child["trace"],"privateTraceFiles":trace_paths})
async def main():
    await one("auto"); await one("legacy")
    print(json.dumps({"sessions":outcomes},sort_keys=True,separators=(",",":")))
asyncio.run(main())
''' % json.dumps(cfg, sort_keys=True, separators=(",", ":"))


def _run_installation(args) -> dict[str, Any]:
    validate_target(args.target)
    manifest_path = args.manifest.resolve(strict=True)
    wheelhouse = args.wheelhouse.resolve(strict=True)
    lock_info = verify_lock_and_wheelhouse(manifest_path, wheelhouse, args.target)
    candidate = args.candidate_wheel.resolve(strict=True)
    candidate_info = candidate_metadata(candidate, args.candidate_sha256)
    assets = candidate_resource_hashes(candidate)
    work = args.work_dir.absolute()
    if work.exists() or work.is_symlink():
        raise ProbeError("work directory must be new")
    work.mkdir(parents=True, mode=0o700)
    os.chmod(work, 0o700)
    home, temp, source, results = (work / name for name in ("home", "tmp", "empty-source", "results"))
    for path in (home, temp, source, results):
        path.mkdir(mode=0o700)
    receipt = {
        "schema": "agent-braid-installed-tooling-probe/v1", "target": args.target,
        "python": sys.version.split()[0], "candidate": candidate_info, "locks": lock_info,
        "commands": [], "registeredAttempt": False, "providerSessionStarted": False,
        "runtimeDispatched": False, "grantIssued": False, "humanEvaluation": False,
    }
    receipt["status"] = "running"
    save_receipt(work, receipt)
    environments = {}
    for flavor in ("core", "tooling"):
        venv = work / "venvs" / flavor
        venv.parent.mkdir(mode=0o700, exist_ok=True)
        initial = safe_environment(Path(sys.executable).parent, home, temp)
        created = run_bounded([sys.executable, "-I", "-m", "venv", str(venv)],
                              cwd=work, env=initial, timeout=45)
        record_command(receipt, work, f"create-{flavor}-venv", created)
        if created.returncode != 0 or created.timed_out or created.output_limited:
            raise ProbeError(f"could not create {flavor} environment")
        python, binary = venv / "bin" / "python", venv / "bin"
        env = safe_environment(binary, home, temp)
        if flavor == "tooling":
            manifest = parse_json_bytes(manifest_path.read_bytes())
            lock_file = (manifest_path.parent / manifest["lockFile"]["path"]).resolve()
            installed_deps = run_bounded([str(python), "-I", "-m", "pip", "install",
                "--no-index", "--find-links", str(wheelhouse), "--require-hashes", "-r", str(lock_file)],
                cwd=work, env=env, timeout=90)
            record_command(receipt, work, "install-locked-sdk-offline", installed_deps)
            if installed_deps.returncode != 0 or installed_deps.timed_out or installed_deps.output_limited:
                raise ProbeError("offline SDK closure install failed")
        installed = run_bounded([str(python), "-I", "-m", "pip", "install",
            "--no-index", "--no-deps", str(candidate)], cwd=work, env=env, timeout=90)
        record_command(receipt, work, f"install-frozen-candidate-{flavor}-offline", installed)
        if installed.returncode != 0 or installed.timed_out or installed.output_limited:
            raise ProbeError(f"candidate install failed in {flavor} environment")
        environments[flavor] = (python, binary, env)

    audits = {}
    for flavor, (python, binary, env) in environments.items():
        audit = run_bounded([str(python), "-I", "-c", _installed_audit_code(assets)],
                            cwd=work, env=env, timeout=30)
        record_command(receipt, work, f"installed-origin-assets-{flavor}", audit)
        if audit.returncode != 0 or audit.timed_out or audit.output_limited:
            raise ProbeError(f"installed origin/assets verification failed for {flavor}")
        audits[flavor] = parse_json_bytes(audit.stdout)
        if audits[flavor].get("assetCount") != 12 or audits[flavor].get("skillCount") != 5:
            raise ProbeError("installed asset count mismatch")
        help_result = run_bounded([str(binary / "agent-braid"), "--help"], cwd=work, env=env, timeout=30)
        record_command(receipt, work, f"console-help-{flavor}", help_result)
        if help_result.returncode != 0 or help_result.timed_out or help_result.output_limited:
            raise ProbeError(f"console help failed for {flavor}")
        if flavor == "core":
            serve = run_bounded([str(binary / "agent-braid"), "tooling", "serve",
                "--source-root", str(source), "--result-root", str(results)],
                cwd=work, env=env, timeout=30)
            record_command(receipt, work, "core-serve-requires-optional-sdk", serve)
            diagnostic = serve.stdout + serve.stderr
            if (serve.returncode != 2 or serve.timed_out or serve.output_limited
                    or b"mcp==2.3.0" not in diagnostic):
                raise ProbeError("core-only MCP serve did not report the expected pending SDK dependency")
            receipt["commands"][-1]["expectedDependencyUnavailable"] = True
        doctor_result = run_bounded([str(binary / "agent-braid"), "tooling", "doctor", "--host", "claude",
            "--scope", "user", "--source-root", str(source), "--result-root", str(results),
            "--destination", str(work / "host-config")], cwd=work, env=env, timeout=30)
        record_command(receipt, work, f"doctor-{flavor}", doctor_result)
        if doctor_result.returncode != 0 or doctor_result.timed_out or doctor_result.output_limited:
            raise ProbeError(f"doctor failed for {flavor}")
        doctor = parse_json_bytes(doctor_result.stdout)
        checks = doctor.get("checks", {})
        sanitized = {key: checks.get(key, {}).get("status") for key in
                     ("protocol", "schemas", "analysis", "authentication", "hostApproval", "runtime")}
        sanitized.update({key: doctor.get(key) for key in ("paidSessionStarted", "runtimeDispatched", "grantIssued")})
        receipt.setdefault("doctor", {})[flavor] = sanitized
        if any(sanitized.get(key) != "pending" for key in
               ("protocol", "schemas", "analysis", "authentication", "hostApproval")):
            raise ProbeError("doctor readiness states were not pending")
        if any(sanitized.get(key) is not False for key in ("paidSessionStarted", "runtimeDispatched", "grantIssued")):
            raise ProbeError("doctor reported an authority effect")

    python, _binary, env = environments["tooling"]
    request = audits["tooling"].get("aimRequest")
    if not isinstance(request, dict):
        raise ProbeError("installed synthetic AIM fixture unavailable")
    request_path = work / "aim-request.json"
    request_path.write_text(json.dumps(request, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.chmod(request_path, 0o600)
    cli_reports = {}
    for flavor, (python, binary, env) in environments.items():
        cli = run_bounded([str(binary / "agent-braid"), "analyze", str(request_path), "--format", "json"],
                          cwd=work, env=env, timeout=30)
        record_command(receipt, work, f"aim-analysis-cli-{flavor}", cli)
        if cli.returncode != 0 or cli.timed_out or cli.output_limited:
            raise ProbeError(f"installed AIM CLI analysis failed for {flavor}")
        report = parse_json_bytes(cli.stdout)
        cli_reports[flavor] = {"reportSha256": canonical_json_sha256(report),
                               "requestSha256": sha256_file(request_path)}
    receipt["aimCli"] = cli_reports
    relay = work / "stdio-relay.py"
    relay.write_text(_relay_source(), encoding="utf-8")
    os.chmod(relay, 0o600)
    relay_config = work / "stdio-relay-config.json"
    relay_config.write_text(json.dumps({
        "argv": [str(python), "-I", "-m", "agent_braid.tooling_mcp", "--source-root",
                 str(source), "--result-parent", str(results)],
        "cwd": str(home), "env": env, "status": str(work / "unset.json"),
        "traces": {},
    }, sort_keys=True), encoding="utf-8")
    os.chmod(relay_config, 0o600)
    receipt["privateRelayArtifacts"] = {
        "configuration": str(relay_config.relative_to(work)),
        "tracePaths": {
            f"{mode}-{name}": f"{mode}-{filename}"
            for mode in ("auto", "legacy")
            for name, filename in {
                "client-to-server": "client-to-server.frames",
                "server-to-client": "server-to-client.frames",
                "server-stderr": "server.stderr.log",
            }.items()
        },
        "statusPaths": {mode: f"{mode}-server-exit.json" for mode in ("auto", "legacy")},
        "limits": {"protocolFrameBytesPerDirection": 1048576, "serverStderrBytes": 65536},
    }
    save_receipt(work, receipt)
    sdk_code = _sdk_probe_code(relay, relay_config, source, results, home, env, request)
    sdk = run_bounded([str(python), "-I", "-c", sdk_code], cwd=work, env=env, timeout=90)
    record_command(receipt, work, "mcp-sdk-auto-legacy", sdk, parent_exit=sdk.returncode)
    attach_relay_observations(work, receipt)
    if sdk.returncode != 0 or sdk.timed_out or sdk.output_limited:
        raise ProbeError("SDK auto/legacy probe failed")
    receipt["sdk"] = parse_json_bytes(sdk.stdout)
    sessions = receipt["sdk"].get("sessions", [])
    if [row.get("mode") for row in sessions] != ["auto", "legacy"]:
        raise ProbeError("SDK negotiation modes incomplete")
    if any(row.get("serverChildReturnCode") != 0 or row.get("serverChildCancelled") is not False
           or row.get("serverChildForcedTermination") is not None or row.get("serverChildReaped") is not True
           for row in sessions):
        raise ProbeError("server child did not exit normally")
    for flavor, cli in cli_reports.items():
        if any(row.get("aimReportSha256") != cli["reportSha256"] for row in sessions):
            raise ProbeError(f"AIM CLI/MCP report parity failed for {flavor}")
    receipt["aimParity"] = {"status": "matched", "cliModes": sorted(cli_reports),
                             "sdkModes": [row["mode"] for row in sessions],
                             "reportSha256": cli_reports["core"]["reportSha256"],
                             "requestSha256": cli_reports["core"]["requestSha256"]}
    receipt["installedAssets"] = {
        flavor: {key: value for key, value in audit.items() if key != "aimRequest"}
        for flavor, audit in audits.items()
    }
    receipt["status"] = "passed"
    save_receipt(work, receipt)
    receipt_path = work / "receipt.json"
    return {"status": "passed", "receiptPath": str(receipt_path),
            "receiptSha256": sha256_file(receipt_path), "target": args.target,
            "candidateSha256": candidate_info["sha256"], "packageCount": lock_info["packageCount"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=sorted(TARGETS), required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--candidate-wheel", type=Path, required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--execute-installed", action="store_true",
                        help="explicitly install the frozen candidate offline")
    args = parser.parse_args(argv)
    try:
        if not args.execute_installed:
            raise ProbeError("refusing install without --execute-installed")
        result = _run_installation(args)
    except (ProbeError, OSError, ValueError, subprocess.SubprocessError) as exc:
        reason = str(exc) if isinstance(exc, ProbeError) else type(exc).__name__
        work = args.work_dir.absolute()
        try:
            mark_blocked_receipt(work, reason)
        except (OSError, ProbeError):
            pass
        print(json.dumps({"status": "blocked", "reason": reason}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
