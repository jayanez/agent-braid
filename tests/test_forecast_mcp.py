# SPDX-License-Identifier: AGPL-3.0-only
import io,json,threading,time,unittest
from agent_braid.forecast_mcp import StdioServer,PROTOCOL,tool_catalog,invoke
from agent_braid.forecast_advice import ForecastSession
from agent_braid.forecast_data import canonical,ForecastError
from tests.test_forecast_session import request

class ForecastMCPTests(unittest.TestCase):
    def test_failed_advice_releases_slot_and_more_than_256_requests_work(self):
        s,out=self.start()
        s.receive(canonical({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'forecast_advice','arguments':{'request':{'forecast':[]}}}}))
        active=s.active
        if active:active[2].join(1)
        self.assertIsNone(s.active)
        for i in range(300):s.receive(canonical({'jsonrpc':'2.0','id':i+3,'method':'ping','params':{}}))
        messages=[json.loads(line) for line in out.getvalue().splitlines()]
        self.assertTrue(messages[1]['result']['isError']);self.assertEqual({},messages[-1]['result']);s.close()

    def test_duplicate_active_id_does_not_release_original_registration(self):
        entered=threading.Event();release=threading.Event()
        class Slow:
            def predict(self,*args,**kwargs):entered.set();release.wait(1);return {'executionAuthorization':False}
            def close(self):pass
        s,out=self.start(Slow());frame={'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'forecast_predict','arguments':{'request':request(),'deadlineMs':1000}}}
        s.receive(canonical(frame));self.assertTrue(entered.wait(1))
        s.receive(canonical(frame));self.assertIn(2,s.seen)
        release.set();s.close();self.assertNotIn(2,s.seen)

    def start(self,session=None):
        out=io.BytesIO();server=StdioServer(session or ForecastSession(),out)
        server.receive(canonical({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':PROTOCOL,'capabilities':{},'clientInfo':{'name':'synthetic','version':'1'}}}))
        server.receive(canonical({'jsonrpc':'2.0','method':'notifications/initialized','params':{}}))
        return server,out

    def test_transport_parity_and_no_execution_tools_or_paths(self):
        self.assertEqual(4,len(tool_catalog()));self.assertTrue(all(t['annotations']['readOnlyHint'] for t in tool_catalog()))
        session=ForecastSession();r=request();actual=invoke(session,'forecast_predict',{'request':r,'deadlineMs':1000})
        self.assertEqual([[4]],actual['median'])
        with self.assertRaises(ForecastError):invoke(session,'execute',{})
        with self.assertRaises(ForecastError):invoke(session,'forecast_predict',{'request':r,'deadlineMs':1000,'path':'/etc/passwd'})
        session.close()

    def test_initialize_discovery_and_completed_ids_can_be_reused(self):
        s,out=self.start();s.receive(canonical({'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}}))
        s.receive(canonical({'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}}))
        values=[json.loads(line) for line in out.getvalue().splitlines()]
        self.assertEqual(4,len(values[1]['result']['tools']));self.assertEqual(values[1]['result'],values[2]['result']);s.close()

    def test_zero_queue_and_request_cancellation(self):
        entered=threading.Event()
        class Slow:
            def predict(self,r,*,deadline,cancellation):
                entered.set();cancellation.wait(1);return {'status':'cancelled','executionAuthorization':False}
            def close(self):pass
        s,out=self.start(Slow());frame={'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'forecast_predict','arguments':{'request':request(),'deadlineMs':1000}}}
        s.receive(canonical(frame));self.assertTrue(entered.wait(1));frame['id']=3;s.receive(canonical(frame))
        s.receive(canonical({'jsonrpc':'2.0','method':'notifications/cancelled','params':{'requestId':2}}));s.close()
        messages=[json.loads(line) for line in out.getvalue().splitlines()]
        self.assertTrue(any(v.get('error',{}).get('message')=='busy-zero-queue' for v in messages))
        self.assertTrue(any(v.get('id')==2 and v.get('result',{}).get('isError') is True for v in messages))
