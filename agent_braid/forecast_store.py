# SPDX-License-Identifier: AGPL-3.0-only
"""Exclusive private receipt files, anchored through no-follow directory descriptors."""
from pathlib import Path
import os
import stat
from .forecast_data import ForecastError,MAX_BYTES,canonical,parse_record,require,digest,pin
from .forecast_receipts import validate_receipt_schema

def verify_receipt(raw):
    return validate_receipt_schema(raw)

def open_directory(path,*,private):
    path=Path(path).absolute();flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
    fd=os.open(path.anchor,flags)
    try:
        for part in path.parts[1:]:
            require(part not in ('.','..'),'unsafe-directory')
            following=os.open(part,flags,dir_fd=fd);os.close(fd);fd=following
        info=os.fstat(fd)
        require(not private or (info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o700),'directory-not-private')
        return fd
    except Exception:os.close(fd);raise

class ReceiptStore:
    def __init__(self,root,*,create=False):
        path=Path(root).absolute()
        if create:
            parent=open_directory(path.parent,private=False)
            try:
                try:os.mkdir(path.name,mode=0o700,dir_fd=parent)
                except FileExistsError:pass
            finally:os.close(parent)
        self.fd=open_directory(path,private=True)

    def put(self,raw):
        require(self.fd is not None,'store-closed');receipt=verify_receipt(raw);name=receipt['packetDigest']+'.json'
        data=canonical(receipt)+b'\n';fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=self.fd)
        try:
            with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
            os.fsync(self.fd)
        except Exception:
            os.unlink(name,dir_fd=self.fd);raise
        return receipt['packetDigest']

    def get(self,receipt_digest):
        require(self.fd is not None,'store-closed');pin(receipt_digest)
        fd=os.open(receipt_digest+'.json',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=self.fd)
        with os.fdopen(fd,'rb') as stream:
            info=os.fstat(stream.fileno());require(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid()
                   and stat.S_IMODE(info.st_mode)==0o600 and info.st_size<=MAX_BYTES+1,'unsafe-receipt-file')
            raw=stream.read(MAX_BYTES+1)
            if raw.endswith(b'\n'):raw=raw[:-1]
            receipt=verify_receipt(parse_record(raw))
        require(receipt['packetDigest']==receipt_digest,'receipt-filename-drift');return receipt

    def close(self):
        if self.fd is not None:os.close(self.fd);self.fd=None

def export_receipt(receipt,destination):
    data=canonical(verify_receipt(receipt))+b'\n';path=Path(destination).absolute()
    fd=open_directory(path.parent,private=False)
    try:
        descriptor=os.open(path.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
        with os.fdopen(descriptor,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.fsync(fd)
    finally:os.close(fd)
