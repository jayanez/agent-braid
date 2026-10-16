# SPDX-License-Identifier: AGPL-3.0-only
"""Separate local stdio JSON-RPC forecasting server with no execution surface."""
from __future__ import annotations
from copy import deepcopy
import sys
import threading
import time
from .forecast_data import ForecastError,MAX_BYTES,canonical,parse_record,keys,require,integer
from .forecast_advice import ForecastSession,capabilities
from .forecast_store import verify_receipt
from .forecast_receipts import inspect_receipt

PROTOCOL='2025-11-25'
TOOLS=('forecast_capabilities','forecast_predict','forecast_advice','forecast_inspect')

def tool_catalog():
    properties={'forecast_capabilities':{},'forecast_predict':{'request':{'type':'object'},'deadlineMs':{'type':'integer','minimum':1,'maximum':31000}},
                'forecast_advice':{'request':{'type':'object'}},'forecast_inspect':{'receipt':{'type':'object'}}}
    return [{'name':name,'description':'Local numeric forecasting; heuristic advice with no execution authority.',
             'inputSchema':{'type':'object','properties':deepcopy(properties[name]),'required':list(properties[name]),'additionalProperties':False},
             'annotations':{'readOnlyHint':True,'destructiveHint':False,'openWorldHint':False}}
            for name in TOOLS]

def invoke(session,name,args,*,cancellation=None):
    require(name in TOOLS,'unsupported-tool')
    if name=='forecast_capabilities':keys(args,());return capabilities()
    if name=='forecast_predict':
        keys(args,('request','deadlineMs'));integer(args['deadlineMs'],1,31000)
        return session.predict(args['request'],deadline=time.monotonic()+args['deadlineMs']/1000,cancellation=cancellation)
    if name=='forecast_advice':keys(args,('request',));return session.advice(args['request'])
    keys(args,('receipt',));return inspect_receipt(args['receipt'])

class StdioServer:
    def __init__(self,session,output):
        self.session=session;self.output=output;self.initialized=False;self.acknowledged=False
        self.writer=threading.Lock();self.state=threading.RLock();self.active=None;self.seen=set();self.closed=False

    def _send(self,value):
        with self.writer:
            if not self.closed:self.output.write(canonical(value)+b'\n');self.output.flush()

    def _error(self,identifier,code,reason,*,release=True):
        try:self._send({'jsonrpc':'2.0','id':identifier,'error':{'code':code,'message':reason}})
        finally:
            if release:
                with self.state:self.seen.discard(identifier)

    def _result(self,identifier,value):
        try:self._send({'jsonrpc':'2.0','id':identifier,'result':value})
        finally:
            with self.state:self.seen.discard(identifier)

    def _execute(self,identifier,name,args,cancel):
        try:
            value=invoke(self.session,name,args,cancellation=cancel)
            if cancel.is_set():raise ForecastError('cancelled')
            result={'content':[{'type':'text','text':canonical(value).decode('ascii')}],'structuredContent':value,'isError':False}
        except Exception:
            reason='cancelled' if cancel.is_set() else 'forecast-request-refused'
            result={'content':[{'type':'text','text':reason}],'isError':True}
        try:self._result(identifier,result)
        except (ForecastError,OSError):
            try:self._error(identifier,-32000,'response-budget-or-output-failure')
            except (ForecastError,OSError):pass
        finally:
            with self.state:
                self.seen.discard(identifier)
                if self.active is not None and self.active[0]==identifier:self.active=None

    def receive(self,raw):
        identifier=None;registered=False
        try:
            frame=parse_record(raw);require(frame.get('jsonrpc')=='2.0','invalid-jsonrpc')
            require(set(frame)<={'jsonrpc','id','method','params'} and type(frame.get('method')) is str,'invalid-frame')
            method=frame['method'];params=frame.get('params',{})
            if 'id' not in frame:
                if method=='notifications/initialized':
                    require(self.initialized and not self.acknowledged,'invalid-initialization');keys(params,());self.acknowledged=True
                elif method=='notifications/cancelled':
                    require(type(params) is dict and set(params)<={'requestId','reason'} and 'requestId' in params,'invalid-cancellation')
                    with self.state:
                        if self.active is not None and self.active[0]==params['requestId']:self.active[1].set()
                else:require(method in ('notifications/progress','notifications/roots/list_changed'),'unsupported-notification')
                return
            identifier=frame['id'];require(type(identifier) in (int,str) and type(identifier) is not bool,'invalid-request-id')
            if type(identifier) is str:require(0<len(identifier)<=128,'invalid-request-id')
            with self.state:
                require(identifier not in self.seen,'duplicate-outstanding-request-id');self.seen.add(identifier);registered=True
            if method=='initialize':
                require(not self.initialized,'already-initialized');require(type(params) is dict and set(params)=={'protocolVersion','capabilities','clientInfo'},'invalid-initialize')
                require(params['protocolVersion']==PROTOCOL and type(params['capabilities']) is dict and type(params['clientInfo']) is dict,'unsupported-protocol')
                self.initialized=True;self._result(identifier,{'protocolVersion':PROTOCOL,'capabilities':{'tools':{}},'serverInfo':{'name':'agent-braid-forecast','version':'0.1.0-alpha'}});return
            require(self.acknowledged,'not-initialized')
            if method=='ping':keys(params,());self._result(identifier,{});return
            if method=='tools/list':keys(params,());self._result(identifier,{'tools':tool_catalog()});return
            require(method=='tools/call','unsupported-method');keys(params,('name','arguments'))
            require(params['name'] in TOOLS and type(params['arguments']) is dict,'unsupported-tool')
            with self.state:
                if self.active is not None:self._error(identifier,-32000,'busy-zero-queue');return
                cancel=threading.Event();worker=threading.Thread(target=self._execute,args=(identifier,params['name'],params['arguments'],cancel),daemon=True)
                self.active=(identifier,cancel,worker);worker.start()
        except (ForecastError,ValueError,KeyError,TypeError):self._error(identifier,-32600,'invalid-or-unsupported-request',release=registered)

    def close(self):
        with self.state:active=self.active
        if active is not None:
            active[1].set();active[2].join(timeout=8)
            require(not active[2].is_alive(),'worker-cleanup-pending')
        self.session.close();self.closed=True

    def serve(self,source):
        try:
            while True:
                raw=source.readline(MAX_BYTES+2)
                if not raw:break
                if len(raw)>MAX_BYTES+1 or not raw.endswith(b'\n'):
                    self._error(None,-32600,'frame-budget-exceeded');break
                self.receive(raw[:-1])
        finally:self.close()

def main(*,session=None):
    try:StdioServer(session or ForecastSession(),sys.stdout.buffer).serve(sys.stdin.buffer);return 0
    except (ForecastError,OSError):return 2

if __name__=='__main__':raise SystemExit(main())
