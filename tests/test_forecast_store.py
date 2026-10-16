# SPDX-License-Identifier: AGPL-3.0-only
import os,stat,tempfile,unittest
from pathlib import Path
from agent_braid.forecast_data import ForecastError
from agent_braid.forecast_store import ReceiptStore,export_receipt
from agent_braid.forecast_baselines import predict_baseline
from agent_braid.forecast_data import digest
from tests.forecast_helpers import window

class ForecastStoreTests(unittest.TestCase):
    def test_self_hashed_arbitrary_json_is_not_a_forecast_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            record={'version':'anything','executionAuthorization':False}
            record['packetDigest']=digest(record)
            with self.assertRaises(ForecastError):export_receipt(record,Path(directory)/'receipt.json')

    def test_owned_immutable_roundtrip_and_exclusive_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();store=ReceiptStore(root/'store',create=True)
            record=predict_baseline(window(),1);key=store.put(record)
            self.assertEqual(record,store.get(key));self.assertEqual(0o600,stat.S_IMODE((root/'store'/(key+'.json')).stat().st_mode))
            with self.assertRaises(FileExistsError):store.put(record)
            export_receipt(record,root/'out.json')
            with self.assertRaises(FileExistsError):export_receipt(record,root/'out.json')
            store.close()

    def test_symlink_public_directory_and_tamper_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();public=root/'public';public.mkdir(mode=0o755)
            with self.assertRaises(ForecastError):ReceiptStore(public)
            (root/'link').symlink_to(public)
            with self.assertRaises(OSError):ReceiptStore(root/'link')
            record=predict_baseline(window(),1);record['median'][0][0]=999
            with self.assertRaises(ForecastError):export_receipt(record,root/'out.json')
