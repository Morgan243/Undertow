from os.path import expanduser, join
import getpass
import unittest
l_host = '127.0.0.1'
l_port = 9876

#from repute.net_core import NetPtr
from undertow.net_core.bsd_socket import NetPtr
from undertow.net_core.ssh_tunnel import tunnel_to, reverse_tunnel
from undertow.wrappers.callback_wrapper import CallbackWrapper

home = expanduser("~")
pkey_path = join(home, '.ssh', 'id_rsa')

class TunnelTests(unittest.TestCase):
    def test_tunnel_build(self):
        srv = tunnel_to(ssh_host=l_host,
                        ssh_port=22,
                        user=getpass.getuser(),
                        ssh_pkey=pkey_path,
                        #ssh_pkey='/home/morgan/.ssh/id_rsa',
                        remote_bind_port=l_port)
        srv.stop()

    def test_reverse_tunnel_build(self):
        return
        srv = reverse_tunnel(ssh_host=l_host,
                             ssh_port=22,
                             user=getpass.getuser(),
                             remote_listen_port=l_port,
                             pkey=pkey_path,
                             allow_prompt=True)
        srv.stop()

    def test_tunnel_connectivity(self):
        pass
        #print("Creating callbacks")
        #cb_container = CallbackWrapper.callbacks(name='test',
        #                                         callback_map=dict())
        #print("Making available")
        #cb_container.make_available(host=l_host, port=l_port)
        #print("Create tunnel")
        #srv = tunnel_to(ssh_host=l_host, ssh_port=22,
        #                remote_bind_port=l_port)
        #print("Stopping server")
        #srv.stop()


        #np1 = NetPtr(host=l_host, port=l_port)
        #np1 = NetPtr(cb_container=cb_container)
        #self.assertEqual(np1.host, l_host)
        #self.assertEqual(np1.port, l_port)

        #self.assertIsNotNone(np1.obj_id)
        #self.assertIsNone(np1.obj)
        #self.assertIsNone(np1.compute_end_t)
        #self.assertIsNone(np1.callbacks)

if __name__ == '__main__':
    unittest.main()
