# SPDX-License-Identifier: AGPL-3.0-only
import hashlib
from pathlib import Path
from types import ModuleType,SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from agent_braid import forecast_worker_entry as entry
from agent_braid.forecast_data import ForecastError,digest

class WorkerEntryCpuBuildTests(unittest.TestCase):
    def test_cpu_distribution_and_binary_build_are_checked_before_checkpoint_construction(self):
        for distribution,cuda,error in [('2.14.1','13.0','cpu-library-version-drift'),
                                        ('2.14.1+cpu','13.0','non-cpu-library-build'),
                                        ('2.14.1+cpu',None,None)]:
            with self.subTest(distribution=distribution,cuda=cuda), tempfile.TemporaryDirectory() as directory:
                root=Path(directory);files={}
                for name in ('config.json','model.safetensors','requirements-cpu.lock'):
                    raw=('synthetic-'+name).encode();(root/name).write_bytes(raw);files[name]=hashlib.sha256(raw).hexdigest()
                load={'command':'load','files':{n:files[n] for n in ('config.json','model.safetensors')},'dependencyLockDigest':files['requirements-cpu.lock'],'coldRemainingSeconds':30,'firstRequest':{'bindingDigest':'a'*64}}
                torch=ModuleType('torch');torch.version=SimpleNamespace(cuda=cuda);torch.backends=SimpleNamespace(cuda=SimpleNamespace(is_built=lambda:cuda is not None))
                torch.float32='stub-float32';torch.set_num_threads=lambda n:None;torch.set_num_interop_threads=lambda n:None
                constructed=[]
                class Pipeline:
                    @staticmethod
                    def from_pretrained(path,**kwargs):constructed.append((path,kwargs));return object()
                chronos=ModuleType('chronos');chronos.Chronos2Pipeline=Pipeline
                def paths(*parts):return root/parts[-1].split('/')[-1]
                versions=lambda name:'2.3.2' if name=='chronos-forecasting' else distribution
                peeks=iter([b'x',b''])
                cg={'memory.max':'2147483648','memory.swap.max':'0','cpu.max':'100000 100000','pids.max':'64'}
                with patch.object(entry,'Path',side_effect=paths),patch.object(entry,'_cg',side_effect=cg.__getitem__), \
                     patch.object(entry,'_read',side_effect=[load,{'command':'predict','bindingDigest':'b'*64}]),patch.object(entry,'_send') as send, \
                     patch('importlib.metadata.version',side_effect=versions), \
                     patch.dict('sys.modules',{'torch':torch,'chronos':chronos}), \
                     patch.object(entry,'_predict',side_effect=[{'status':'forecast','bindingDigest':'a'*64},{'status':'forecast','bindingDigest':'b'*64}]) as predict, \
                     patch.object(entry.signal,'setitimer') as timer,patch.object(entry.signal,'signal'), \
                     patch.object(entry.sys,'stdin',SimpleNamespace(buffer=SimpleNamespace(peek=lambda n:next(peeks)))):
                    if error:
                        with self.assertRaisesRegex(ForecastError,error):entry.main()
                        self.assertEqual([],constructed)
                    else:
                        self.assertEqual(0,entry.main());self.assertEqual(1,len(constructed))
                        self.assertEqual('cpu',constructed[0][1]['device_map'])
                        self.assertTrue(constructed[0][1]['local_files_only']);self.assertFalse(constructed[0][1]['trust_remote_code'])
                        self.assertEqual({'status':'forecast','bindingDigest':'a'*64,'libraryVersion':'2.3.2'},send.call_args_list[1].args[0])
                        self.assertEqual(2,predict.call_count);timer.assert_any_call(entry.signal.ITIMER_REAL,30)
                        timer.assert_any_call(entry.signal.ITIMER_REAL,1)

    def test_prediction_binding_rejects_changed_first_input_before_pipeline(self):
        request={'command':'predict','inputs':[],'horizon':1,'inputDigest':'a'*64}
        request['bindingDigest']=digest(request);request['horizon']=5
        class Pipeline:
            def predict_quantiles(self,*args,**kwargs):self.fail('unbound request reached pipeline')
        with self.assertRaisesRegex(ForecastError,'worker-input-binding'):
            entry._predict(Pipeline(),None,request)
