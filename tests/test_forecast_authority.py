# SPDX-License-Identifier: AGPL-3.0-only
import hashlib,json,os,tempfile,time,unittest
from pathlib import Path
from agent_braid.forecast_authority import DeploymentArtifactVerifier
from agent_braid.forecast_data import ForecastError,digest
from tests.test_forecast_worker import manifest

class DeploymentAuthorityTests(unittest.TestCase):
    def test_self_hashed_record_is_not_admitted_without_separate_pin_and_revocation_is_live(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();root.chmod(0o700);record=root/'decision.json';registry=root/'pins.json';m=manifest()
            raw=json.dumps({'version':'agent-braid-owner-artifact-approval-v1','approved':True,'authority':'owner-artifact-compute',
                'manifestDigest':digest(m),'scope':'local-cpu-synthetic-conformance','expiresUnixNs':time.time_ns()+10000000000,
                'sourceReference':'synthetic-authority-control-not-human-approval'}).encode()
            record.write_bytes(raw);record.chmod(0o600);verifier=DeploymentArtifactVerifier(registry=registry)
            with self.assertRaises(ForecastError):verifier.verify(m)
            registry.write_text(json.dumps({'version':'agent-braid-owner-approval-pins-v1','approvals':[{'manifestDigest':digest(m),
                'recordPath':str(record),'recordSha256':hashlib.sha256(raw).hexdigest()}]}));registry.chmod(0o600)
            self.assertEqual(digest(m),verifier.verify(m).manifest_digest)
            record.write_bytes(raw+b' ')
            with self.assertRaises(ForecastError):verifier.verify(m)
            record.write_bytes(raw);self.assertIsNotNone(verifier.verify(m));record.unlink()
            with self.assertRaises(ForecastError):verifier.verify(m)
            registry.unlink()
            with self.assertRaises(ForecastError):verifier.verify(m)
