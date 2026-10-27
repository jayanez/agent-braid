# SPDX-License-Identifier: AGPL-3.0-only
"""Offline native-provider parser/state controls; kernel and process I/O mocked."""
import unittest
from agent_braid.forecast_data import ForecastError
from agent_braid.forecast_native import proc_stat, ChildObserver
from agent_braid.forecast_recipe import tree_oid, overlay


class RecipeMetadataTests(unittest.TestCase):
    def test_git_tree_encoding_and_disjoint_overlay(self):
        self.assertEqual(tree_oid({}), '4b825dc642cb6eb9a060e54bf8d69288fbee4904')
        base={'a':('100644','1'*40)}
        a={**base,'d/b':('100644','2'*40)}
        b={'a':('100644','3'*40)}
        result,changes=overlay(base,a,b)
        self.assertEqual(result,{**b,'d/b':('100644','2'*40)})
        self.assertEqual(changes,[['d/b'],['a']])

    def test_overlap_delete_mode_and_path_collision_refuse(self):
        base={'a':('100644','1'*40)}
        cases=[({},base),({'a':('100755','1'*40)},base),
               ({'a':('100644','2'*40)},{'a':('100644','3'*40)}),
               ({**base,'d':('100644','2'*40)},{**base,'d/b':('100644','3'*40)})]
        for a,b in cases:
            with self.subTest(a=a), self.assertRaises(ForecastError):
                overlay(base,a,b)


class ProcStateTests(unittest.TestCase):
    def test_comm_parentheses_do_not_shift_kernel_fields(self):
        values=['0']*50
        values[0]='Z';values[1]='101';values[19]='1234';values[49]='1792'
        result=proc_stat('202 (git ) with spaces) '+' '.join(values))
        self.assertEqual(result,{'pid':202,'state':'Z','ppid':101,'start':1234,'exitStatus':1792})

    def test_child_exit_is_observed_before_reap_and_pid_reuse_refuses(self):
        from unittest.mock import patch
        observer=ChildObserver(worker_pid=101,worker_cgroup='/scope',git_sha256='a'*64,working_directory='/work',git_identity=(1,2))
        invocation={'argv':['git','status'],'env':{'HOME':'/work/home'},'cwd':None,
                    'inputSha256':None,'inheritedFds':[]}
        live={'pid':202,'ppid':101,'state':'S','start':1234,'exitStatus':0}
        zombie={**live,'state':'Z','exitStatus':1792}
        with patch.object(observer.view,'guard'), \
             patch.object(observer.view,'state',side_effect=[live,live,zombie]), \
             patch.object(observer.view,'ready',side_effect=[False,False,True,True]), \
             patch.object(observer.view,'executable'), \
             patch.object(observer.view,'read',side_effect=[b'0::/scope\n',b'git\0status\0',b'HOME=/work/home\0']), \
             patch('agent_braid.forecast_native.os.pidfd_open',return_value=55,create=True), \
             patch('agent_braid.forecast_native.os.readlink',return_value='/work'), \
             patch('agent_braid.forecast_native.os.stat',return_value=type('Info',(),{'st_dev':1,'st_ino':2})()), \
             patch('agent_braid.forecast_native.os.close') as close:
            self.assertTrue(observer(202,'launched',invocation)['identityVerified'])
            self.assertEqual(observer(202,'exited',invocation)['returncode'],7)
            self.assertEqual(observer(202,'reaped',invocation),{'terminated':True,'returncode':7})
        close.assert_called_once_with(55)

    def test_reap_without_zombie_observation_fails_closed(self):
        from unittest.mock import patch
        observer=ChildObserver(worker_pid=101,worker_cgroup='/scope',git_sha256='a'*64,working_directory='/work',git_identity=(1,2))
        from agent_braid.forecast_data import digest
        observer.children[202]={'fd':55,'invocation':digest({})}
        with patch.object(observer.view,'guard'), patch.object(observer.view,'ready',return_value=True):
            with self.assertRaises(ForecastError):
                observer(202,'reaped',{})
        self.assertTrue(observer.failed)

    def test_reused_pid_at_zombie_stage_never_closes_ticket(self):
        from unittest.mock import patch
        from agent_braid.forecast_data import digest
        observer=ChildObserver(worker_pid=101,worker_cgroup='/scope',git_sha256='a'*64,working_directory='/work',git_identity=(1,2))
        observer.children[202]={'fd':55,'invocation':digest({}),'state':{'start':1234}}
        with patch.object(observer.view,'guard'),patch.object(observer.view,'ready',return_value=True), \
             patch.object(observer.view,'state',return_value={'pid':202,'ppid':101,'start':9999,'state':'Z'}):
            with self.assertRaises(ForecastError):
                observer(202,'exited',{})
        self.assertIn(202,observer.children)


class QualificationQuotaTests(unittest.TestCase):
    def test_terminal_close_reaps_root_control_and_closes_handles_even_on_failure(self):
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        from agent_braid.forecast_native import NativeBoundary
        for failure in (False,True):
            provider=object.__new__(NativeBoundary)
            provider.session=SimpleNamespace(timeline=SimpleNamespace(index=4))
            provider.root_gate=MagicMock(cleanup_confirmed=not failure,exit_status=0 if not failure else None)
            provider.census=MagicMock();provider.child_observer=MagicMock()
            if failure:
                provider.root_gate.stop.side_effect=ForecastError('uncertain')
                with self.assertRaisesRegex(ForecastError,'uncertain'):provider.close_control()
            else:provider.close_control()
            provider.root_gate.stop.assert_called_once();provider.census.close.assert_called_once()
            provider.child_observer.close.assert_called_once()
            self.assertEqual(provider.root_gate_closure['cleanupConfirmed'],not failure)
            self.assertFalse(provider.root_gate_closure['nativeCoverageAccepted'])

    def provider(self,index):
        from types import SimpleNamespace
        from agent_braid.forecast_native import NativeBoundary,KernelView
        obj=object.__new__(NativeBoundary)
        obj.profile=SimpleNamespace(identity='a'*64,uid=61000,
            limits=[SimpleNamespace(storage_bytes=4096,inodes=8)]*5)
        obj.session=SimpleNamespace(timeline=SimpleNamespace(index=index),quota=SimpleNamespace(bytes=4096,inodes=8))
        obj.view=KernelView()
        return obj

    def test_all_five_phases_require_exact_tmpfs_before_release(self):
        from unittest.mock import patch
        for index in range(5):
            provider=self.provider(index)
            phase='prepare' if index<3 else ('verify' if index==3 else 'terminal')
            path='/run/fc1/'+'a'*64+'/'+phase
            raw=(f'1 0 0:1 / {path} rw,nosuid,nodev,noexec - tmpfs tmpfs '
                 'rw,noswap,mode=700,uid=61000,gid=61000,size=4k,nr_inodes=8\n').encode()
            with self.subTest(index=index),patch.object(provider.view,'read',return_value=raw):
                provider._quota_readback()
            with patch.object(provider.view,'read',return_value=raw.replace(b'size=4k',b'size=8k')):
                with self.assertRaises(ForecastError):
                    provider._quota_readback()

    def test_host_platform_guard_prevents_any_tool_launch(self):
        from unittest.mock import patch
        from agent_braid.forecast_native import NativeBoundary
        provider=object.__new__(NativeBoundary)
        from agent_braid.forecast_native import KernelView
        provider.view=KernelView()
        with patch('agent_braid.forecast_native.sys.platform','darwin'), \
             patch('agent_braid.forecast_native.subprocess.Popen') as spawn:
            with self.assertRaises(ForecastError):
                provider._tool('/usr/bin/systemctl','show')
        spawn.assert_not_called()

class SnapshotSafetyTests(unittest.TestCase):
    def test_image_ancestor_symlink_and_foreign_mount_refuse(self):
        import stat
        from types import SimpleNamespace
        from pathlib import Path
        from unittest.mock import patch
        from agent_braid.forecast_native import NativeBoundary
        provider=object.__new__(NativeBoundary)
        good=SimpleNamespace(st_dev=1,st_mode=stat.S_IFDIR|0o755)
        for bad in (SimpleNamespace(st_dev=1,st_mode=stat.S_IFLNK|0o777),
                    SimpleNamespace(st_dev=2,st_mode=stat.S_IFDIR|0o755)):
            with patch('agent_braid.forecast_native.os.stat',return_value=good), \
                 patch.object(Path,'lstat',return_value=bad):
                with self.assertRaisesRegex(ForecastError,'symlink-or-mount'):
                    provider._image_path(123,Path('/proc/123/root/opt/source'))

    def test_tool_snapshot_rejects_wrong_bytes_before_memfd(self):
        from unittest.mock import patch,MagicMock
        from agent_braid.forecast_native import NativeBoundary
        provider=object.__new__(NativeBoundary)
        provider.view=MagicMock();provider.view.read.return_value=b'drift'
        provider.tool_pins={'/usr/bin/systemctl':'a'*64}
        with patch('agent_braid.forecast_native.os.memfd_create',create=True) as create:
            with self.assertRaisesRegex(ForecastError,'tool-drift'):
                provider._sealed_tool('/usr/bin/systemctl')
        create.assert_not_called()

    def test_aggregate_operator_and_worker_quotas_all_required(self):
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        from agent_braid.forecast_native import NativeBoundary
        provider=object.__new__(NativeBoundary)
        stem='fc1'+'a'*64
        aggregate=Path('/sys/fs/cgroup')/(stem+'.slice')
        worker=aggregate/(stem+'-workers.slice')
        root=aggregate/(stem+'-root.slice')
        operator=root/(stem+'-operator.service')
        provider.profile=SimpleNamespace(identity='a'*64,operator_sha256='b'*64)
        provider.session=SimpleNamespace(work=SimpleNamespace(path=worker/(stem+'-prepare.service')))
        rows={'/proc/self/cgroup':('0::/'+str(operator.relative_to('/sys/fs/cgroup'))+'\n').encode()}
        for group,mem,tasks in ((aggregate,3221225472,96),(worker,2147483648,64),(root,536870912,16)):
            for key,value in [('cpu.max','100000 100000'),('memory.max',str(mem)),
                              ('memory.swap.max','0'),('pids.max',str(tasks))]:
                rows[str(group/key)]=value.encode()
        provider.view=MagicMock();provider.view.read.side_effect=lambda p,*a:rows[str(p)]
        from unittest.mock import patch
        provider.operator_identity=None
        info=SimpleNamespace(st_dev=1,st_ino=2)
        with patch('agent_braid.forecast_native.os.stat',return_value=info):
            provider._cgroup_quotas()
            provider._cgroup_quotas()
            provider.view.executable.assert_called_once()
            rows[str(root/'memory.max')]=b'max'
            with self.assertRaisesRegex(ForecastError,'cgroup-quota'):
                provider._cgroup_quotas()
            with patch('agent_braid.forecast_native.os.stat',return_value=SimpleNamespace(st_dev=1,st_ino=3)):
                with self.assertRaisesRegex(ForecastError,'executable-replaced'):
                    provider._cgroup_quotas()
