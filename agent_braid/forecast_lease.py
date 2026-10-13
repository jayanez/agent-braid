# SPDX-License-Identifier: AGPL-3.0-only
"""Cross-process one-container admission with persistent unresolved-cleanup state."""
import fcntl
import os
from pathlib import Path
import stat
from .forecast_data import canonical,parse_record,require,ForecastError,identifier,pin
from .forecast_store import open_directory

class WorkerLease:
    def __init__(self,owner,manifest_digest,*,directory=None):
        self.owner=identifier(owner);self.manifest_digest=pin(manifest_digest);self.fd=None
        self.directory=Path(directory) if directory is not None else Path.home()/'.local/state/agent-braid/forecast'

    def acquire(self):
        self.directory.mkdir(parents=True,exist_ok=True,mode=0o700)
        directory_fd=open_directory(self.directory,private=True)
        try:fd=os.open('cpu-worker.lease',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600,dir_fd=directory_fd)
        finally:os.close(directory_fd)
        try:
            info=os.fstat(fd);require(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid()
                 and stat.S_IMODE(info.st_mode)==0o600 and info.st_size<=4096,'unsafe-worker-lease')
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise ForecastError('worker-busy') from None
            raw=os.read(fd,4096)
            if raw:require(parse_record(raw).get('cleanupConfirmed') is True,'owned-container-cleanup-pending')
            self.fd=fd;self._write(False)
        except Exception:os.close(fd);raise

    def _write(self,cleaned):
        record={'owner':self.owner,'manifestDigest':self.manifest_digest,'cleanupConfirmed':cleaned}
        raw=canonical(record);os.lseek(self.fd,0,os.SEEK_SET);os.write(self.fd,raw);os.ftruncate(self.fd,len(raw));os.fsync(self.fd)

    def release(self,*,cleanup_confirmed):
        if self.fd is None:return
        try:self._write(cleanup_confirmed)
        finally:fcntl.flock(self.fd,fcntl.LOCK_UN);os.close(self.fd);self.fd=None
