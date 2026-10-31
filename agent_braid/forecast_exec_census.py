# SPDX-License-Identifier: AGPL-3.0-only
"""Private numeric kernel census: read-only BPF access, never loads/attaches probes.

The external operator must supply independently reviewed program hashes. A hash
observed from the kernel is never adopted as its own authority. Real coverage,
attachment before the first worker, and final closure need native qualification.
"""
import ctypes
import hashlib
import os
from pathlib import Path
import struct

from .forecast_data import pin, require
from research.lab.model import loads

CAPACITY = 65536
EVENT = struct.Struct('<QQQQIIII')  # sequence, monotonic ns, flow cg, task cg, pid,tgid,kind,reserved


def decode_event(raw, sequence, cgroup):
    require(len(raw) == EVENT.size, 'census-record-size')
    seq, ns, flow, task, pid, tgid, kind, reserved = EVENT.unpack(raw)
    require(seq == sequence and ns > 0 and flow == cgroup and task > 0
            and pid > 0 and tgid > 0 and kind in (1, 2, 3) and reserved == 0,
            'census-record-binding')
    return dict(sequence=seq, ns=ns, taskCgroup=task, pid=pid, tgid=tgid, kind=kind)


class CensusLedger:
    """Pure bounded reconciliation; remaining execs are conservatively unclassified.

    Limits are abort policies, not predictions of necessary helpers. Every event
    retains its denominator. No PID-only deduplication across multiple execs.
    """
    def __init__(self, profile, origin_ns):
        self.profile = profile
        self.origin_ns = origin_ns
        self.events = []
        self.known = set()
        self.closed = -1
        self.rows = []

    def reconcile(self, raw_records, *, cgroup, phase, deadline_ns, known=()):
        require(phase == self.closed+1 and len(self.events)+len(raw_records) <= CAPACITY,
                'census-phase-or-capacity')
        new = [decode_event(raw, len(self.events)+i+1, cgroup)
               for i, raw in enumerate(raw_records)]
        require(all(self.origin_ns <= e['ns'] < deadline_ns for e in new), 'census-time-boundary')
        known_set = set(known)
        require(self.known <= known_set and all(type(key) is tuple and len(key) == 2
                    and key[1] in ('git','tool','worker') and type(key[0]) is int and key[0] > 0
                    for key in known_set), 'census-known-binding')
        # Closed phase classifications cannot be rewritten by a later known PID.
        pending = list(sorted(known_set-self.known))
        added_known = list(pending)
        used = set()
        for i,e in enumerate(new):
            if e['kind'] == 2:
                match = next((key for key in pending if key[0] == e['pid']), None)
                if match:
                    used.add(i); pending.remove(match)
        require(not pending, 'census-missing-known-exec')
        auxiliary = sum(e['kind'] == 2 and i not in used for i,e in enumerate(new))
        git = self.profile.limits[phase].requests
        require(sum(k[1]=='git' for k in added_known) <= git
                and sum(k[1]=='tool' for k in added_known) <= 3
                and sum(k[1]=='worker' for k in added_known) <= int(phase in (0,3,4)),
                'census-known-cap')
        require(auxiliary <= git, 'census-auxiliary-cap')
        self.events,self.known,self.closed = self.events+new,known_set,phase
        row = dict(phaseIndex=phase,events=len(new),execs=sum(e['kind']==2 for e in new),
                   knownExecs=len(added_known),auxiliaryOrUnclassified=auxiliary,
                   auxiliaryAbortCap=git,lost=0,nativeCoverageAccepted=False)
        self.rows.append(row)
        return dict(row)


class KernelCensus:
    """Linux 6.12 aarch64 UAPI; only commands lookup(1), obj-get(7), info(15).

    No map writes, program load, attachment or enumeration of other workloads.
    Generic operator-reviewed probes expose cfg/state/events and three raw links.
    Event ABI and immutable program semantics must be reviewed before acceptance.
    """
    def __init__(self, profile, manifest_bytes, view):
        require(len(manifest_bytes) <= 16384 and hashlib.sha256(manifest_bytes).hexdigest()
                == profile.census_sha256, 'census-manifest-pin')
        manifest = loads(manifest_bytes.decode())
        require(set(manifest) == {'version','programs'} and manifest['version'] == 'fc1-census-v1'
                and set(manifest['programs']) == {'fork','exec','exit'}, 'census-manifest-fields')
        for value in manifest['programs'].values(): pin(value)
        self.profile,self.view,self.manifest = profile,view,manifest
        self.fds = {}; self.cgroup = None; self.qualified = False

    def _bpf(self, command, attr):
        self.view.guard()
        require(os.uname().machine == 'aarch64' and command in (1,7,15), 'census-readonly-uapi')
        buf = ctypes.create_string_buffer(attr)
        libc = ctypes.CDLL(None, use_errno=True); libc.syscall.restype = ctypes.c_long
        result = libc.syscall(ctypes.c_long(280), ctypes.c_long(command), ctypes.byref(buf), ctypes.c_uint(len(attr)))
        require(result >= 0, 'census-kernel-read-failed')
        return result

    def _get(self, name, *, map_object=False):
        path = Path('/sys/fs/bpf/fc1')/self.profile.identity/name
        for part in (path.parent, path):
            info = part.lstat()
            require(info.st_uid == 0 and not part.is_symlink() and not info.st_mode & 0o077,
                    'census-pin-permissions')
        raw = ctypes.create_string_buffer(os.fsencode(path))
        fd = self._bpf(7, struct.pack('<QII', ctypes.addressof(raw), 0, 8 if map_object else 0))
        os.set_inheritable(fd, False); self.fds[name] = fd
        return fd

    def _info(self, fd, initial=b''):
        value = ctypes.create_string_buffer(256)
        if initial: ctypes.memmove(value, initial, len(initial))
        self._bpf(15, struct.pack('<IIQ', fd, 256, ctypes.addressof(value)))
        self.view.account(256)
        return value.raw

    def _lookup(self, name, key, size):
        k = ctypes.c_uint(key); value = ctypes.create_string_buffer(size)
        self._bpf(1, struct.pack('<IIQQQ', self.fds[name], 0, ctypes.addressof(k), ctypes.addressof(value), 0))
        self.view.account(size)
        return value.raw

    def qualify(self, cgroup):
        self.view.guard(); self.cgroup = cgroup
        if not self.fds:
            try:
                maps = set()
                for name,size,count in [('fc1_cfg',32,1),('fc1_state',32,1),('fc1_evts',48,CAPACITY)]:
                    info = self._info(self._get(name, map_object=True))
                    typ,identity,key,val,maximum,flags = struct.unpack_from('<6I', info)
                    require((typ,key,val,maximum,flags) == (2,4,size,count,0)
                            and info[24:40].split(b'\0')[0].decode() == name, 'census-map-layout')
                    maps.add(identity)
                require(len(maps)==3,'census-distinct-maps')
                for name in ('fork','exec','exit'):
                    label=ctypes.create_string_buffer(64); initial=bytearray(256)
                    struct.pack_into('<QI',initial,16,ctypes.addressof(label),64)
                    link=self._info(self._get(name+'_link'),initial)
                    typ,_,program=struct.unpack_from('<III',link)
                    require(typ==1 and label.value.decode()=='sched_process_'+name,'census-link-target')
                    code=ctypes.create_string_buffer(65536); ids=(ctypes.c_uint*16)()
                    initial=bytearray(256);struct.pack_into('<I',initial,20,65536)
                    struct.pack_into('<Q',initial,32,ctypes.addressof(code))
                    struct.pack_into('<I',initial,52,16);struct.pack_into('<Q',initial,56,ctypes.addressof(ids))
                    info=self._info(self._get(name+'_program'),initial)
                    typ,identity=struct.unpack_from('<II',info)
                    length=struct.unpack_from('<I',info,20)[0]; count=struct.unpack_from('<I',info,52)[0]
                    require(typ==17 and identity==program and 0<length<=65536 and count==3
                            and set(ids[:count])==maps,'census-program-links')
                    self.view.account(length)
                    require(hashlib.sha256(code.raw[:length]).hexdigest()==self.manifest['programs'][name],
                            'census-program-pin')
            except BaseException:
                self.close();raise
        cfg=struct.unpack('<QQIIQ',self._lookup('fc1_cfg',0,32))
        require(cfg==(cgroup,int(self.profile.identity[:16],16),1,0,1),'census-cgroup-epoch')
        self.qualified=True
        self.check_live()

    def check_live(self):
        require(self.qualified,'census-unqualified')
        cfg=struct.unpack('<QQIIQ',self._lookup('fc1_cfg',0,32))
        require(cfg==(self.cgroup,int(self.profile.identity[:16],16),1,0,1),'census-config-drift')
        for name in ('fork','exec','exit'):
            info=self._info(self.fds[name+'_program'])
            require(struct.unpack_from('<Q',info,208)[0]==0,'census-recursion-miss')
        allocated,written,lost,reserved=struct.unpack('<QQQQ',self._lookup('fc1_state',0,32))
        require(not lost and not reserved and 0<=written<=allocated<=CAPACITY,'census-loss-or-overflow')
        return allocated,written

    def snapshot(self, cursor, *, frozen):
        frozen()
        before=self.check_live()
        require(before[0]==before[1] and 0<=cursor<=before[0],'census-inflight-or-rewind')
        rows=[self._lookup('fc1_evts',i,48) for i in range(cursor,before[0])]
        frozen()
        require(self.check_live()==before,'census-changing-boundary')
        return rows

    def close(self):
        for fd in self.fds.values(): os.close(fd)
        self.fds.clear();self.qualified=False
