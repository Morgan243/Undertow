import os
import struct
import threading
import time
import socket
import pickle
import sys
from queue import Queue

import undertow.utils as utils
from undertow import configuration as conf
from undertow.net_core.net_ptr import NetPtr
from undertow.net_core.serializer import serialize, deserialize
#from undertow.net_core.net_connection import NetConnection
thread = utils.thread

NET_CORE_STOP_EVENT = threading.Event()
BROADCAST_PORT = 2438
MULTICAST_GROUP_IP = '224.3.29.71'
MULTICAST_GROUP = (MULTICAST_GROUP_IP, BROADCAST_PORT)
TTL = 1

callback_q = Queue()

logger = utils.setup_logger(name=__name__)


class NetCore:

    #tunnel_map = dict()
#    @staticmethod
#    def reset_connections():
#        """
#        Closses
#        :return:
#        """
#        [nc.socket.close() for nc in NetCore.tunnel_map.values()]
#        NetCore.tunnel_map = dict()

    @staticmethod
    def get_net_address(return_one=True):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:

           net_addresses = [na for na in [s.connect(('8.8.8.8', 53)), s.getsockname()[0]]
                            if na not in ('127.0.0.1', '::1')]

        if len(net_addresses) == 0:
            raise ValueError("No non local host net addresses found")

        if return_one:
            return net_addresses[0]
        else:
            return net_addresses

    @staticmethod
    def build_socket():
        """
        Build a basic TCP socket (AF_INET + SOCK_STREAM) and set
        it to reusable (REUSEADDR option set to 1).

        :return: Socket object
        """
        sock = socket.socket(family=socket.AF_INET,
                             type=socket.SOCK_STREAM)

        sock.setsockopt(socket.SOL_SOCKET, # level
                        socket.SO_REUSEADDR, # option
                        1) # value
        return sock

    #TODO: Remove NetConnection use -
    # NetConnection manages tunnels and sockets
#    @staticmethod
#    def build_client_socket(host, port, tunnel=None):
#        if tunnel is None:
#            tunnel = conf.tunnel
#        #print("Client socket to %s, %s" % (str(host), str(port)))
#        k = "%s-%s" % (host, port)
#        try:
#            net_conn = NetCore.tunnel_map[k]
#        except KeyError as e:
#            net_conn = NetConnection(host, port)
#
#            is_local = host in ('127.0.0.1', 'localhost', '::1')
#            if is_local:
#                print("BUILDING LOCAL CLIENT SOCKET")
#            else:
#                print("BUILDING non local CLIENT SOCKET")
#            if is_local and conf.tunnel_for_local_connections:
#                net_conn.open_tunnel()
#            elif not is_local and tunnel:
#                net_conn.open_tunnel()
#
#        if net_conn.socket is None:
#            net_conn.connect_existing_socket(NetCore.build_socket())

#        NetCore.tunnel_map[k] = net_conn

#        return net_conn.socket

    @staticmethod
    def build_listen_socket(host, port,
                            timeout=1,
                            listen_size=50,
                            increment_until_success=False):
        host = host if host is not None else ''
        port = port if port is not None else 0
        if increment_until_success:
            while True:
                try:
                    sock = NetCore.build_listen_socket(host, port, timeout, False)
                    return sock
                except:
                    if port < 1000:
                        port = 1001
                    else:
                        port += 1
        else:
            sock = NetCore.build_socket()
            sock.bind((host, port))
            sock.settimeout(timeout)
            sock.listen(listen_size)

            return sock



        #if on_disconnect is not None:
        #    on_disconnect()

        #conn.close()



#    @staticmethod
#    def start_listener(sock, callbacks, callback_container_map=None, in_subproc_callbacks=None,
#                       on_connect=None, on_disconnect=None,
#                       register_func=None, pass_connections_list=None,
#                       stop_event=None):
#        if stop_event is None:
#            stop_event = NET_CORE_STOP_EVENT
#
#        logger.debug("Netcore listener started")
#        thread_kwargs = dict(stop_event=stop_event,
#                             pass_connection_list=pass_connections_list,
#                             origin_listen_port=sock.getsockname()[1])
#        callback_thread = thread(target=NetCore.callback_worker,
#                                 kwargs=thread_kwargs,
#                                 name='Callback worker')
#
#        listening_threads = []
#        while not stop_event.isSet():
#            try:
#                conn, addr = sock.accept()
#                if on_connect is not None:
#                    on_connect()
#                targs = [conn, callbacks, None, on_disconnect, pass_connections_list,
#                         sock.getsockname()[1], in_subproc_callbacks]
#                if len(callbacks) > 0:
#                    t = thread(target=NetCore.handle_client,
#                               args=targs)
#                    listening_threads.append(t)
#
#                dead_threads = [lt for lt in listening_threads if not lt.isAlive()]
#                listening_threads = [lt for lt in listening_threads if lt.isAlive()]
#                # print("%d client(s) now connected" % len(listening_threads))
#
#                if len(dead_threads) > 0:
#                    logger.debug("Removing %d disconnected clients" % len(dead_threads))
#                    [dt.join() for dt in dead_threads]
#
#            # Socket not blocking indefinitely, catch timeout
#            except socket.timeout as e:
#                #logger.info("Socket timeout")
#                continue
#            # When connection breaks
#            except OSError as e:
#                sock.close()
#                break
#            except:
#                raise
#                break

#        print("Netcore listener ended")
#        logger.debug("Netcore listener ended")
#        return listening_threads


    @staticmethod
    def send_object(sock, obj):
        payload = serialize(obj)
        message = struct.pack('>I', len(payload)) + payload
        return sock.sendall(message)

    @staticmethod
    def receive_all_bytes(sock, expected_bytes):
        data = sock.recv(expected_bytes)
        while len(data) < expected_bytes:
            packet = sock.recv(expected_bytes - len(data))
            if not packet:
                return None
            data += packet
        return data

    @staticmethod
    def receive_object(sock):
        raw_len = NetCore.receive_all_bytes(sock, 4)
        if not raw_len:
            return None
        raw_len = struct.unpack('>I', raw_len)[0]
        raw_bytes = NetCore.receive_all_bytes(sock, raw_len)
        return deserialize(raw_bytes)

    @staticmethod
    def send_then_receive_response(sock, obj):
        NetCore.send_object(sock, obj)
        return NetCore.receive_object(sock)


class BroadcastCore:
    @staticmethod
    def build_socket():
        """Build a UDP socket, suitable for broadcasting"""
        sock = socket.socket(family=socket.AF_INET,
                             type=socket.SOCK_DGRAM)

        sock.setsockopt(socket.SOL_SOCKET,
                        socket.SO_REUSEADDR, 1)

        return sock

    @staticmethod
    def build_broadcast_socket(ttl=1):
        """Socket setup to send out broadcasts"""
        sock = BroadcastCore.build_socket()

        ttl = struct.pack('b', ttl)
        sock.setsockopt(socket.IPPROTO_IP,
                        socket.IP_MULTICAST_TTL, ttl)
        #sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 4)
        #ttl = struct.pack('@i', 2)
        #sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        return sock

    @staticmethod
    def build_listen_socket(port=None, timeout=2):
        """Socket setup to receive broadcasts"""
        port = BROADCAST_PORT if port is None else port
        sock = BroadcastCore.build_socket()
        #sock.bind(('<broadcast>', port))
        sock.bind(('', port))

        group = socket.inet_aton(MULTICAST_GROUP_IP)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        sock.settimeout(timeout)

        ##
        #MCAST_GRP = '224.1.1.1'
        #MCAST_PORT = 5007
        #sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        #sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
        #sock.sendto('Hello World!', (MCAST_GRP, MCAST_PORT))

        return sock

    @staticmethod
    def send_broadcast(msg, sock=None, multicast_group=MULTICAST_GROUP,
                       ttl=TTL):
        if sock is None:
            sock = BroadcastCore.build_broadcast_socket(ttl=ttl)

        if type(msg) == str:
            msg = bytes(msg, encoding='utf-8')

        amnt = 0.0
        while amnt < len(msg):
            amnt += sock.sendto(msg, multicast_group)

        return amnt

    @staticmethod
    def listen_for_broadcasts(port=BROADCAST_PORT, callback=lambda x, y, ev: ev.set(),
                              size=128, timeout=4, sock=None,
                              stop_on_timeout=False, stop_event=None):
        """
        Will continuously listen for broadcast data. Whenever broadcast data
        is received, the provided callback function is passed an identifying
        (address, port) tuple and raw data received as a bytes string.

        Parameters
        ----------
        port : int (default=BROADCAST_PORT)
            Port to listen for broadcasts on
        callback : callable (default=lambda x, y: True)
            Callable accepting two positional arguments. The
            first being a tuple of (host, port) of type (str, int) and the
            second being the raw data that was broadcast as a bytes object
        size : int (default=64)
            The amount of bytes to receive
        timeout : int (default=3)
            Timeout on the listening socket. This mostly
            irrelevant unless the stop_on_timeout parameter is True.
        sock : socket.socket (default=None)
            A pre-constructed listening socket. If None,
            one is built.
        stop_on_timeout : boolean (default=False)
            If True, the call will exit after timeout
            has reached.
        Returns
        -------
        Client Info and Data : Tuple
            Tuple of bytes data and (addr, port)
        """
        if stop_event is None:
            stop_event = threading.Event()
        if sock is None:
            sock = BroadcastCore.build_listen_socket(port,
                                                     timeout=timeout)

        recv_data, addr = None, None
        while not stop_event.is_set():
            try:
                recv_data, addr = sock.recvfrom(size)
                if callback is not None:
                    callback(addr, recv_data, stop_event)
            except socket.timeout as e:
                if stop_on_timeout:
                    break
                continue
            except OSError as e:
                if e.errno == 9: # Bad File descriptor, thrown on shutdown
                    sock.close()
                    break
                else:
                    raise

        return recv_data, addr

    @staticmethod
    def is_self_sent(recv_addr, recv_data, this_addr, sent_data):
        #print("Comparing: %s | %s" %(str(recv_addr), str(this_addr)))
        if recv_addr[1] == this_addr[1] and recv_data == sent_data:
            return True
        else:
            return False

    @staticmethod
    def bcast_and_recv_responses(data, listen_socket=None, broadcast_socket=None,
                                 max_responses=100, timeout=2):
        #raise ValueError("Don't need to have a conversation over broadcasts!")
        if listen_socket is None:
            listen_sock = BroadcastCore.build_listen_socket()

        if broadcast_socket is None:
            broadcast_socket = BroadcastCore.build_broadcast_socket()

        BroadcastCore.send_broadcast(data, sock=broadcast_socket)
        this_addr = broadcast_socket.getsockname()

        received = list()
        while True:
            data, addr = BroadcastCore.listen_for_broadcasts(sock=listen_socket,
                                                             timeout=timeout,
                                                             stop_on_timeout=True)
            if data is None and addr is None:
                break

            self_sent = BroadcastCore.is_self_sent(addr, data,
                                                   this_addr, data)
            if not self_sent:
                received.append((data, addr))
            else:
                pass

            if len(received) >= max_responses:
                break
        return received


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Broadcasting")
        BroadcastCore.send_broadcast("hello-0.01:billy")
    else:
        print("Launching broadcast listener")
        stop, listener = BroadcastCore.launch_broadcast_listener()
        listener.join()

