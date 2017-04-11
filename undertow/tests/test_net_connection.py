import time
import unittest
import random

from undertow.net_core.net_connection import NetBroadcast, NetConnection
from undertow.tests.test_broadcast_core import *
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

l_host = '127.0.0.1'
l_port = 9999

class NetConnectionTests(unittest.TestCase):
    def test_get_id(self):
        id1 = NetBroadcast().get_id()
        id2 = NetBroadcast().get_id()
        self.assertNotEqual(id1, id2)


    def test_listen_for_broadcasts(self):
        bcast = NetBroadcast(callback=bcast_received).launch_broadcast_listener()
        bcast.broadcast('foo')

    def test_start_listener(self):
        #NetCore.reset_connections()
        global check_set
        global on_connect_set
        global on_disconnect_set

        rand_set_val = random.randint(0, 100)
        srv = NetConnection(host=l_host, port=l_port).listen()
        t = Thread(target=srv.serial_accept,
                   kwargs=dict(callback=lambda cxn: cb(cxn.receive())))
        t.daemon = True
        t.start()
        time.sleep(.25)
        clnt = NetConnection(host=l_host, port=l_port).connect()
        clnt.send('hello')
        time.sleep(.25)
        self.assertEqual(check_set, 'hello')
        clnt.close()
        srv.close()
        time.sleep(1)
        print(clnt)
        print(srv)



        #l_sock = NetCore.build_listen_socket(host=l_host,
        #                                     port=l_port,
        #                                     timeout=1,
        #                                     increment_until_success=False)

        #callbacks = dict(test_cb=cb)
        # TODO: Rethink on_connect & on_disconnect
        #listener_kwargs = dict(
        #                       cb_wrapper=CallbackWrapper.callbacks(name='test234', callback_map=callbacks).make_available(host=l_host, port=l_port),
                               #on_connect=on_conn_func,
                               #on_disconnect=on_disconn_func
        #                       )

        #l_thread = Thread(target=NetCore.start_listener,
        #                  kwargs=listener_kwargs,
        #                  daemon=True)
        #cb = CallbackWrapper().callbacks(name='tesssst',)

        #l_thread = Thread(target=NetCore.callback_listener,
        #                  kwargs=listener_kwargs,
        #                  daemon=True)
        #l_thread.start()
        #time.sleep(.4)

        #ret = NetCore.exec_remote_callback(rand_set_val,
        #                                   host=l_host,
        #                                   port=l_port,
        #                                   cb_func='test_cb')

        #self.assertEqual(rand_set_val, check_set)
        # TODO: see above
        #self.assertTrue(on_connect_set)
        #self.assertEqual(ret, 'foobar')

        # On disconnect isn't called until
        # after the call is made, so wait
        # for race to play out and do it last
        #time.sleep(.2)
        # TODO: see above
        #self.assertTrue(on_disconnect_set)