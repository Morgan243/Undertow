import unittest
l_host = '127.0.0.1'
l_port = 9876

#from repute.net_core import NetPtr
from undertow.net_core.bsd_socket import NetPtr
from undertow.wrappers.callback_wrapper import CallbackWrapper

g_val = None
def cb(val):
    global g_val
    g_val = val
    return 'hi'


class NetPtrTests(unittest.TestCase):
    def test_construction(self):
        #cb_container = CallbackWrapper.callbacks(name='test', callback_map=dict())
        #cb_container.make_available(host=l_host, port=l_port)
        #np1 = NetPtr(host=l_host, port=l_port)
        #NetPtr(callback_func=cb_test, callback_args='what')
        np1 = NetPtr(callback_func=cb,
                     callback_args=['args'],
                     callback_kwargs=dict(),
                     return_output=True)
        np1.run_callback_request()

        #self.assertEqual(np1.host, l_host)
        #self.assertEqual(np1.port, l_port)

        self.assertIsNotNone(np1.uid)
        self.assertTrue(np1.obj == 'hi')
        self.assertIsNotNone(np1.compute_end_t)
        #self.assertIsNone(np1.callbacks)

if __name__ == '__main__':
    unittest.main()
