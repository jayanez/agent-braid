# SPDX-License-Identifier: AGPL-3.0-only
import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from tests.test_forecast_session import request

class ForecastCLITests(unittest.TestCase):
    def test_capabilities_help_and_predict_load_no_ml(self):
        code='from agent_braid.cli import main;import sys;main(["forecast","capabilities"]);assert not any(x in sys.modules for x in ("torch","chronos","transformers"))'
        result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=5)
        self.assertEqual(0,result.returncode,result.stderr);self.assertEqual('off',json.loads(result.stdout)['defaultMode'])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'input.json';path.write_text(json.dumps(request()))
            result=subprocess.run([sys.executable,'-m','agent_braid','forecast','predict',str(path)],capture_output=True,text=True,timeout=5)
            self.assertEqual(0,result.returncode,result.stderr);self.assertEqual([[4]],json.loads(result.stdout)['median'])

    def test_oversized_malformed_input_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'input.json';path.write_text('{"window":NaN}')
            result=subprocess.run([sys.executable,'-m','agent_braid','forecast','predict',str(path)],capture_output=True,text=True,timeout=5)
            self.assertEqual(2,result.returncode);self.assertFalse(json.loads(result.stdout)['executionAuthorization'])
