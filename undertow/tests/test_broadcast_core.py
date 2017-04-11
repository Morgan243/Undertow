import unittest
import time
import unittest
import random
#import repute.net_core as nc
#from repute.net_core import BroadcastCore
from undertow.net_core.bsd_socket import BroadcastCore
from undertow.net_core.net_connection import NetBroadcast
from threading import Thread, Semaphore, Condition, RLock

from socket import socket
l_host = '127.0.0.1'
l_port = 9876
bcast_sem = Semaphore(value=0)
bcast_set = None

def bcast_received(addr, recv_data, ev):
    global bcast_set
    print(addr)
    print(recv_data)
    print(type(recv_data))
    bcast_set = True
    bcast_sem.release()
    ev.set()
    #return True


class BroadcastCoreTests(unittest.TestCase):
    def test_build_socket(self):
        sock = BroadcastCore.build_socket()
        self.assertIsInstance(sock, socket)

    def test_build_broadcast_socket(self):
        sock = BroadcastCore.build_broadcast_socket()
        self.assertIsInstance(sock, socket)

    def test_build_bcast_listen_socket(self):
        sock = BroadcastCore.build_listen_socket()
        self.assertIsInstance(sock, socket)

    def test_client_broadcast_to_listen(self):
        #t = Thread(target=BroadcastCore.listen_for_broadcasts,
                   #kwargs=dict(callback=bcast_received))
        #t.daemon = True
        #t.start()
        # Give the listener a second to come up before broadcasting
        bcast = NetBroadcast(bcast_received).launch_broadcast_listener()
        time.sleep(7)
        #amnt = BroadcastCore.send_broadcast('foo')
        amnt = NetBroadcast().broadcast('foo')
        bcast_sem.acquire(timeout=5)

        self.assertEqual(bcast_set, True)
        self.assertTrue(amnt > 0)
        bcast.close()

    def test_broadcast_and_recv(self):
        callback = lambda addr, data, ev: BroadcastCore.send_broadcast('bary')
        bcast = NetBroadcast(callback=callback).launch_broadcast_listener()

        #t = Thread(target=lambda : BroadcastCore.listen_for_broadcasts())
        #t = Thread(target=BroadcastCore.listen_for_broadcasts,
        #           kwargs=dict(callback=lambda addr, data, ev: BroadcastCore.send_broadcast('bary')))
        #t.daemon = True
        #t.start()
        # Give the listener a second to come up before broadcasting
        time.sleep(.25)
        #received = BroadcastCore.bcast_and_recv_responses('wooh')
        received = NetBroadcast().broadcast_then_receive('wooh')
        self.assertTrue(len(received) > 0 )
        self.assertTrue(any(d == b'bary' for d, addr in received))
        bcast.close()


if __name__ == '__main__':
    unittest.main()
