import time
import unittest
print("test")
from undertow import service as s
from undertow.wrappers.multi_remote_output_wrapper import MultiRemoteOutputWrapper
from undertow.tests.test_service import test_class as tc


class TestContainers(unittest.TestCase):
    def test_discover(self):
        print("testing discover")
        with s.ServiceModule.launch(tc('oof1', 'rab1'), port=1257) as stc1:
            with s.ServiceModule.launch(tc('oof2', 'rab1'), port=1258) as stc2:
                time.sleep(3)
                rs = s.ServiceModule.discover(tc)
                print(rs)
                self.assertIsInstance(rs, s.RemoteServiceWrapper)
                self.assertNotIsInstance(rs, list)
                self.assertNotIsInstance(rs, s.MultiRemoteServiceWrapper)

                rs = s.ServiceModule.discover(tc, return_one=False)
                print(rs)
                self.assertIsInstance(rs, s.MultiRemoteServiceWrapper)
                self.assertNotIsInstance(rs, list)
                self.assertNotIsInstance(rs, s.RemoteServiceWrapper)

                rs_res = rs.foo_cb()
                self.assertIsInstance(rs_res, MultiRemoteOutputWrapper)
                print(rs_res.values)

                vals = list(rs_res.values)
                #ttest = 'oof2' in vals and 'oof1' in vals
                #self.assertTrue(ttest)

if __name__ == '__main__':
    unittest.main()
