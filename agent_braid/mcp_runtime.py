# SPDX-License-Identifier: AGPL-3.0-only
"""Version-pinned stdio MCP adapter for an operator-configured owned runtime.

No authorization tool, network listener, host credential or arbitrary command.
The actual policy enforces authority independently of MCP tool annotations.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import signal
import sys
import threading

from research.lab.model import Invalid, loads
from .analysis import _digest
from . import git_runtime, git_replay, runtime_policy, runtime_scheduler
from .git_process import GitInfrastructureFailure

PROTOCOL = '2025-11-25'
MAX_FRAME = 1024 * 1024
TOOL_TIMEOUT_SECONDS = 360
TOOLS = ('analyze', 'prepare', 'status', 'execute', 'recover', 'verify')


class InvalidMcpRuntime(ValueError):
    """Invalid protocol parameters or out-of-scope local resource."""


def _require(condition, message):
    if not condition:
        raise InvalidMcpRuntime(message)


def _identifier(value):
    return type(value) is int or (type(value) is float and math.isfinite(value)) or (
        isinstance(value, str) and 0 < len(value) <= 256)


def _parse_frame(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError('duplicate object member')
            result[key] = value
        return result
    def constant(_value):
        raise ValueError('nonfinite JSON number')
    def number(value):
        result=float(value)
        if not math.isfinite(result): raise ValueError('JSON number exceeds finite range')
        return result
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                      parse_constant=constant, parse_float=number)


def tool_catalog():
    definitions = []
    for name in TOOLS:
        if name in {'analyze','prepare'}:
            properties = {'request': {'type':'object'}}
            required = ['request']
            if name == 'prepare':
                properties['runDirectory'] = {'type':'string'}
                properties['mode'] = {'enum':['serial','parallel']}
                required.append('runDirectory')
        else:
            properties = {'plan': {'type':'object'}}
            required = ['plan']
            if name in {'execute','recover'}:
                properties['grantId'] = {'type':'string'}
                required.append('grantId')
            if name == 'recover':
                properties['action'] = {'enum':['resume','abort']}
                required.append('action')
        definitions.append({'name':name,
                            'description':'Bounded private Git runtime '+name+'. Evidence and tool annotations grant no execution authority.',
                            'inputSchema':{'type':'object','additionalProperties':False,
                                           'properties':properties,'required':required},
                            'annotations':{'readOnlyHint':name not in {'execute','recover'},
                                           'destructiveHint':name=='recover',
                                           'openWorldHint':False}})
    return definitions


class RuntimeTools:
    def __init__(self, source_root: Path, result_parent: Path, grant_store: Path):
        self.source = source_root.resolve(strict=True)
        self.results = result_parent.resolve(strict=True)
        self.grants = grant_store.absolute()
        _require(self.source.is_dir() and self.results.is_dir(), 'configured roots must exist')
        _require(not self.results.is_relative_to(self.source), 'result parent overlaps source')
        _require(not self.grants.is_relative_to(self.source), 'grant store overlaps source')

    def _request_scope(self, request):
        _require(isinstance(request,dict) and isinstance(request.get('repository'),str), 'missing runtime source')
        _require(Path(request['repository']).expanduser().absolute()==self.source,
                 'source is outside the operator-configured root')

    def _destination_scope(self, value):
        _require(isinstance(value,str), 'invalid private destination')
        path=Path(value).expanduser().absolute()
        _require(path.parent==self.results, 'destination is outside the configured result parent')
        _require(path.name not in {'','.','..'} and not path.is_symlink(), 'invalid result name')

    def invoke(self, name, args, cancel_event):
        _require(name in TOOLS, 'unknown runtime tool')
        _require(isinstance(args,dict), 'tool arguments must be an object')
        definition = next(d for d in tool_catalog() if d['name']==name)['inputSchema']
        _require(set(definition['required']) <= set(args) <= set(definition['properties']),
                 'unknown or missing tool arguments')
        _require(not cancel_event.is_set(), 'tool cancelled before starting a phase')
        if name in {'analyze','prepare'}:
            request=args['request']; self._request_scope(request)
            normalized=git_runtime._request(request)
            evidence, advisory=git_replay.produce(git_runtime._analysis_request(normalized))
            _require(not cancel_event.is_set(), 'tool cancelled after bounded analysis')
            if name=='analyze':
                return {'evidence':evidence,'advisoryPlan':advisory,'executionAuthorization':False}
            self._destination_scope(args['runDirectory'])
            mode=args.get('mode','serial')
            _require(isinstance(mode,str) and mode in {'serial','parallel'}, 'invalid preparation mode')
            return runtime_policy.prepare_policy_run(normalized,args['runDirectory'],
                                                      replay_evidence=evidence,advisory_plan=advisory,
                                                      cancel_event=cancel_event, mode=mode)
        plan=args['plan']
        _require(isinstance(plan,dict) and isinstance(plan.get('runtimeManifest'),dict), 'missing policy plan')
        manifest=plan['runtimeManifest']
        self._request_scope(manifest.get('request'))
        self._destination_scope(manifest.get('runDirectory'))
        if name in {'verify','status'}:
            return runtime_policy.inspect_policy_run(plan,self.grants,cancel_event=cancel_event)
        identifier=args['grantId']
        _require(isinstance(identifier,str), 'operator grant ID must be a string')
        if name=='execute':
            return runtime_policy.execute_policy_run(plan,self.grants,identifier,cancel_event=cancel_event)
        return runtime_policy.recover_policy_run(plan,self.grants,identifier,action=args['action'],cancel_event=cancel_event)


class StdioServer:
    def __init__(self, runtime, output):
        self.runtime=runtime; self.output=output
        self.initializing=False; self.initialized=False; self.closed=False
        self.output_lock=threading.Lock(); self.active_lock=threading.Lock()
        self.active={}; self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='braid-mcp')

    def _write(self, payload):
        encoded=(json.dumps(payload,separators=(',',':'),ensure_ascii=False)+'\n').encode()
        if len(encoded)>MAX_FRAME:
            payload={'jsonrpc':'2.0','id':payload.get('id'),'error':{'code':-32603,'message':'Response exceeds frame limit; inspect runtime state before retry'}}
            encoded=(json.dumps(payload)+'\n').encode()
        with self.output_lock:
            if not self.closed:
                try: self.output.write(encoded);self.output.flush()
                except (BrokenPipeError,OSError): self.cancel_all()

    def error(self, identifier, code, message):
        self._write({'jsonrpc':'2.0','id':identifier,'error':{'code':code,'message':message}})

    def result(self, identifier, value):
        self._write({'jsonrpc':'2.0','id':identifier,'result':value})

    def cancel_all(self):
        self.closed=True
        with self.active_lock:
            for event in self.active.values(): event.set()

    def _finish(self, identifier, future):
        try:
            value=future.result()
            with self.active_lock: event=self.active.get(identifier)
            _require(event is not None and not event.is_set(),
                     'Tool cancelled; inspect private state before retry')
            result={'content':[{'type':'text','text':json.dumps(value,separators=(',',':'))}],
                    'structuredContent':value,'isError':False}
        except (InvalidMcpRuntime,runtime_policy.InvalidRuntimePolicy,git_runtime.InvalidGitRuntime,
                git_replay.InvalidGitReplay,runtime_scheduler.InvalidRuntimeSchedule,
                GitInfrastructureFailure,Invalid,OSError,UnicodeError) as exc:
            result={'content':[{'type':'text','text':str(exc)[:2048]}],'isError':True}
        except Exception:
            # Unexpected defects are explicit failures; diagnostics stay off the tool surface.
            result={'content':[{'type':'text','text':'Internal runtime failure; inspect private state before retry'}],'isError':True}
        with self.active_lock: self.active.pop(identifier,None)
        self.result(identifier,result)

    def receive(self, frame):
        _require(isinstance(frame,dict) and frame.get('jsonrpc')=='2.0'
                 and isinstance(frame.get('method'),str), 'invalid JSON-RPC request')
        _require(set(frame) <= {'jsonrpc','id','method','params'}, 'unknown JSON-RPC fields')
        method=frame['method']; notification='id' not in frame
        identifier=frame.get('id')
        _require(notification or _identifier(identifier), 'invalid MCP request ID')
        params=frame.get('params',{})
        _require(isinstance(params,dict), 'parameters must be an object')
        if notification:
            if method=='notifications/initialized':
                _require(self.initializing and not self.initialized, 'unexpected initialized notification')
                self.initialized=True
            elif method=='notifications/cancelled':
                target=params.get('requestId')
                _require(_identifier(target), 'invalid cancellation ID')
                with self.active_lock:
                    event=self.active.get(target)
                    if event is not None: event.set()
            return
        if method=='initialize':
            _require(not self.initializing, 'session is already initialized')
            _require(isinstance(params.get('protocolVersion'),str)
                     and isinstance(params.get('capabilities'),dict)
                     and isinstance(params.get('clientInfo'),dict), 'invalid initialize parameters')
            info=params['clientInfo']
            _require(isinstance(info.get('name'),str) and isinstance(info.get('version'),str), 'invalid client identity')
            self.initializing=True
            self.result(identifier,{'protocolVersion':PROTOCOL,'capabilities':{'tools':{}},
                                    'serverInfo':{'name':'agent-braid-bounded-runtime','version':'0.1.0-alpha'}})
            return
        if method=='ping':
            self.result(identifier,{});return
        if method not in {'tools/list','tools/call'}:
            self.error(identifier,-32601,'Method not found');return
        _require(self.initialized, 'session has not completed initialization')
        if method=='tools/list':
            _require(set(params) <= {'cursor','_meta'} and not params.get('cursor'), 'unsupported tools cursor')
            self.result(identifier,{'tools':tool_catalog()});return
        _require(set(params) <= {'name','arguments','_meta'} and isinstance(params.get('name'),str),
                 'invalid tool call parameters')
        _require(isinstance(params.get('arguments',{}),dict), 'tool arguments must be an object')
        if params['name'] not in TOOLS:
            self.error(identifier,-32602,'Unknown tool');return
        with self.active_lock:
            duplicate=identifier in self.active
            if not duplicate:
                _require(not self.active, 'runtime tool is busy; retry after inspecting the active operation')
                event=threading.Event();self.active[identifier]=event
        if duplicate:
            self.error(None,-32600,'Duplicate active request ID; original operation remains active')
            return
        timer=threading.Timer(TOOL_TIMEOUT_SECONDS,event.set)
        timer.daemon=True;timer.start()
        try:
            future=self.pool.submit(self.runtime.invoke,params['name'],params.get('arguments',{}),event)
        except RuntimeError:
            timer.cancel()
            with self.active_lock: self.active.pop(identifier,None)
            raise InvalidMcpRuntime('Runtime executor unavailable; no tool was dispatched')
        def completed(future):
            timer.cancel()
            self._finish(identifier,future)
        future.add_done_callback(completed)

    def serve(self, stream):
        try:
            while not self.closed:
                raw=stream.readline(MAX_FRAME+1)
                if not raw: break
                if len(raw)>MAX_FRAME:
                    self.error(None,-32600,'Frame exceeds 1 MiB');break
                try:
                    frame=_parse_frame(raw)
                except (Invalid,ValueError,UnicodeError,RecursionError):
                    self.error(None,-32700,'Parse error');continue
                valid = (isinstance(frame,dict) and frame.get('jsonrpc')=='2.0'
                         and isinstance(frame.get('method'),str)
                         and set(frame) <= {'jsonrpc','id','method','params'}
                         and ('id' not in frame or _identifier(frame['id'])))
                if not valid:
                    self.error(None,-32600,'Invalid JSON-RPC request');continue
                try: self.receive(frame)
                except InvalidMcpRuntime as exc:
                    identifier=frame.get('id') if isinstance(frame,dict) else None
                    if not _identifier(identifier): identifier=None
                    if 'id' in frame: self.error(identifier,-32602,str(exc))
        finally:
            self.cancel_all();self.pool.shutdown(wait=True,cancel_futures=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--result-parent',type=Path,required=True)
    parser.add_argument('--grant-store',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        tools=RuntimeTools(args.source_root,args.result_parent,args.grant_store)
        server=StdioServer(tools,sys.stdout.buffer)
        def stop(_signum,_frame):
            server.cancel_all()
            raise KeyboardInterrupt
        previous={signum:signal.signal(signum,stop) for signum in (signal.SIGINT,signal.SIGTERM)}
        try: server.serve(sys.stdin.buffer)
        except KeyboardInterrupt: pass
        finally:
            for signum,handler in previous.items():signal.signal(signum,handler)
        return 0
    except (InvalidMcpRuntime,OSError) as exc:
        print(str(exc),file=sys.stderr);return 2


if __name__=='__main__': raise SystemExit(main())
