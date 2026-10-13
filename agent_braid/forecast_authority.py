# SPDX-License-Identifier: AGPL-3.0-only
"""Injected external artifact authority, never populated by numeric requests."""
import hashlib
import os
import stat
import time
from dataclasses import dataclass
from typing import Protocol
from .forecast_data import require,pin,digest

@dataclass(frozen=True)
class ArtifactApprovalAttestation:
    manifest_digest: str
    source_record_digest: str
    authority: str

class ArtifactApprovalVerifier(Protocol):
    def verify(self,manifest:dict) -> ArtifactApprovalAttestation | None:
        """Verify actual owner artifact/compute approval against retained sources."""

def require_artifact_approval(manifest,verifier):
    require(verifier is not None,'artifact-not-approved')
    attestation=verifier.verify(manifest)
    require(type(attestation) is ArtifactApprovalAttestation and attestation.authority=='owner-artifact-compute',
            'artifact-not-approved')
    require(attestation.manifest_digest==digest(manifest),'artifact-approval-drift')
    pin(attestation.source_record_digest);return attestation


def _private_record(path):
    from pathlib import Path
    from .forecast_store import open_directory
    from .forecast_data import parse_record
    path=Path(path).absolute();parent=open_directory(path.parent,private=True)
    try:fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
    finally:os.close(parent)
    try:
        info=os.fstat(fd);require(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid()
             and stat.S_IMODE(info.st_mode)==0o600 and info.st_size<=65536,'unsafe-owner-record')
        with os.fdopen(fd,'rb',closefd=False) as stream:raw=stream.read(65537)
    finally:os.close(fd)
    return parse_record(raw.strip()),hashlib.sha256(raw).hexdigest()

class DeploymentArtifactVerifier:
    """Fixed deployment trust anchor; no request or launch argument can pin itself.

    The registry is installed separately by the trusted owner deployment process,
    after retaining an actual decision. Its filesystem ownership is the local
    trust boundary, not cryptographic proof of a human action. Tests may inject
    a private fixture registry; CLI/MCP cannot select a registry or record hash.
    Every verify re-reads both pins and record, making removal/change revocation.
    """
    def __init__(self,*,registry=None):
        from pathlib import Path
        self.registry=Path(registry) if registry is not None else Path.home()/'.config/agent-braid/forecast/owner-approval-pins.json'

    def verify(self,manifest):
        from pathlib import Path
        from .forecast_data import keys,integer,ForecastError
        try:
            registry,_=_private_record(self.registry);keys(registry,('version','approvals'))
            require(registry['version']=='agent-braid-owner-approval-pins-v1','unsupported-deployment-registry')
            approvals=registry['approvals'];require(type(approvals) is list and len(approvals)<=16,'invalid-deployment-pins')
            seen=set();entry=None
            for item in approvals:
                keys(item,('manifestDigest','recordPath','recordSha256'));identity=pin(item['manifestDigest']);pin(item['recordSha256'])
                require(identity not in seen and type(item['recordPath']) is str and Path(item['recordPath']).is_absolute(),'invalid-deployment-pin')
                seen.add(identity)
                if identity==digest(manifest):entry=item
            require(entry is not None,'artifact-not-approved')
            r,observed=_private_record(entry['recordPath']);require(observed==entry['recordSha256'],'owner-record-revoked-or-drifted')
            keys(r,('version','approved','authority','manifestDigest','scope','expiresUnixNs','sourceReference'))
            integer(r['expiresUnixNs']);require(type(r['sourceReference']) is str and 0<len(r['sourceReference'])<=256,'missing-owner-source')
            require(r['version']=='agent-braid-owner-artifact-approval-v1' and r['approved'] is True
                    and r['authority']=='owner-artifact-compute' and r['scope']=='local-cpu-synthetic-conformance'
                    and time.time_ns()<r['expiresUnixNs'] and r['manifestDigest']==digest(manifest),'artifact-not-approved')
            return ArtifactApprovalAttestation(digest(manifest),observed,r['authority'])
        except (OSError,ValueError,KeyError,TypeError):raise ForecastError('artifact-not-approved') from None
