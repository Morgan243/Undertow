import time
import unittest
import random

from undertow.net_core.net_connection import NetConnection
from undertow.net_core.bsd_socket import NetCore
from undertow.wrappers.callback_wrapper import CallbackWrapper
from threading import Thread

from socket import socket
l_host = '127.0.0.1'
l_port = 9999

# Vars that callbacks will set, global so they
# can be easily verified in the tests
check_set = None
on_connect_set = None
on_disconnect_set = None


def cb(value):
    global check_set
    check_set = value
    return 'foobar'

def on_conn_func():
    global on_connect_set
    on_connect_set = True

def on_disconn_func():
    global on_disconnect_set
    on_disconnect_set = True


class NetCoreTests(unittest.TestCase):
    def test_build_socket(self):
        sock = NetCore.build_socket()
        self.assertIsInstance(sock, socket)

    def test_build_listen_socket(self):
        l_sock = NetCore.build_listen_socket(host=l_host,
                                             port=l_port,
                                             timeout=1,
                                             increment_until_success=False)
        l_sock.close()

    def test_client_connect_to_listen(self):
        l_netcon = NetConnection(host=l_host, port=l_port)
        l_netcon.listen()

        netcon = NetConnection(host=l_host, port=l_port)
        netcon.connect()
        netcon.close()
        l_netcon.close()



if __name__ == '__main__':
    unittest.main()
