import os
import time
import unittest
from undertow.service import ServiceModule
from undertow.service import Expose
from undertow.service import Worker
from undertow.registry import launch_registry, discover_registry
from undertow.net_core.bsd_socket import NetCore
from undertow.net_core.net_connection import NetConnection

import random

@Expose('foobarclass')
class test_class:
    def __init__(self, foo, bar):
        self.foo = foo
        self.bar = bar

    @Expose()
    def add_one(self, n):
        return n + 1

    @Expose(container_type='process')
    def process_get_pid(self):
        return os.getpid()

    @Expose(container_type='thread')
    def thread_get_pid(self):
        return os.getpid()

    @Expose(container_type='thread')
    def slow_to_process(self, delay=10):
        time.sleep(delay)
        return random.randint(0, 10)

    @Expose()
    def foo_cb(self):
        return self.foo

    @Worker()
    def bar_wrk(self):
        self.bar_wrk = str(self.bar) + 'wrked'


class TestServiceModule2(unittest.TestCase):

    def test_class_decorator(self):
        NetConnection.reset_connections()

        self.assertIsInstance(test_class.UNDERTOW, dict)

        tc = test_class('fooy', 'bary')
        self.assertIsInstance(tc, test_class)
        self.assertIn('foobarclass', ServiceModule.alias_to_entity_id)

        with ServiceModule.launch(tc, port=1357) as svc:
            svc.wait_on_workers()

            self.assertEqual(tc.bar_wrk, 'barywrked')

            rs = ServiceModule.remote_service(host='127.0.0.1', port=1357)
            self.assertEqual(rs.foo_cb(), 'fooy')

            thr_pid = rs.thread_get_pid()
            proc_pid = rs.process_get_pid()

            print("Thread pid: %d" % thr_pid)
            print("Proc pid: %d" % proc_pid)

            self.assertEqual(thr_pid, os.getpid(),
                             "Thread pid call doesn't match unittest pid")
            self.assertNotEqual(proc_pid, os.getpid(),
                                "SubProcess pid call matches unittest pid")

    def test_discovery(self):
        tc = test_class('fooy', 'bary')

        with ServiceModule.launch(tc, port=1357, bcast_response=True) as svc:
            remote = ServiceModule.discover(test_class, return_one=True)
            self.assertEqual(remote.foo_cb(), 'fooy')

    def test_registry(self):
        tc2 = test_class('fooery', 'baryer')

        # Todo: Expose callbacks locally? Or Just use registry? Maybe nest real object in Launched service
        reg = launch_registry()
        remote_reg = discover_registry()
        with ServiceModule.launch(tc2, port=1359, reg=remote_reg) as svc:
            foo_hosts = remote_reg.get_hosts_of_service('foobarclass')

            #self.assertIn(('0.0.0.0', 1359), foo_hosts)


            self.assertIn('foobarclass', [p['service_name'] for p in foo_hosts])

            rs_tc = ServiceModule.remote_service_from_registry('foobarclass', remote_reg=remote_reg)
            self.assertEqual(rs_tc.foo_cb(), 'fooery')
        reg.close()

    def test_map(self):
        with ServiceModule.launch(test_class('oof1', 'rab1'), port=1257) as stc1:
            with ServiceModule.launch(test_class('oof2', 'rab1'), port=1258) as stc2:
                rs = ServiceModule.discover(test_class, return_one=False)
                res = rs.map('add_one', iterable_args=[[1], [2], [3]])

                res = rs.map('slow_to_process', iterable_kwargs=[dict(delay=10),
                                                                 dict(delay=20)])
                self.assertIsNotNone(res)

    def test_map_seq(self):
        with ServiceModule.launch(test_class('oof1', 'rab1'), port=1257) as stc1:
            with ServiceModule.launch(test_class('oof2', 'rab1'), port=1258) as stc2:
                rs = ServiceModule.discover(test_class, return_one=False)

                res = rs.map_sequence(['add_one', 'slow_to_process'],
                                        [dict(n=n) for n in range(3)], dict(delay=5) )
                #res = rs.map('add_one', iterable_args=[[1], [2], [3]])

                #res = rs.map('slow_to_process', iterable_kwargs=[dict(delay=10),
                #                                                dict(delay=20)])
                self.assertIsNotNone(res)
                self.assertTrue(hasattr(res, 'add_one'))

                self.assertIsInstance(res.add_one, list)
                self.assertTrue(res.add_one[0] == 1)
                self.assertTrue(res.add_one[1] == 2)
                self.assertTrue(res.add_one[2] == 3)

                self.assertIsInstance(res.slow_to_process, list)
                self.assertIsInstance(res.slow_to_process[0], int)
                self.assertIsInstance(res.slow_to_process[1], int)
                self.assertIsInstance(res.slow_to_process[2], int)

if __name__ == '__main__':
    unittest.main()
