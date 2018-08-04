import socket
import uuid
import attr
from getpass import getpass
from undertow.net_core.ssh_tunnel import tunnel_to
from undertow.net_core.bsd_socket import NetCore, BroadcastCore, BROADCAST_PORT
from undertow import utils
#from undertow.utils import thread
import threading

try:
    from queue import Queue
except ImportError as e:
    from Queue import Queue

logger = utils.setup_logger(name='NetConnection')
from undertow import configuration as conf


@attr.attributes
class NetConnection(object):
    net_cxn_lock = threading.Lock()
    pw_cache = dict()

    # Map host/ports/service to existing sockets/tunnel
    existing_cxn_map = dict()
    existing_tunnel_map = dict()

    # Map host/ports/service to objects using it
    existing_cxn_users = dict()
    existing_tunnel_users = dict()

    host = attr.attr(default=None)
    port = attr.attr(default=None)
    tunnel = attr.attr(default=None)

    socket = attr.attr(default=None)
    is_connected = attr.attr(default=False, init=False)
    is_listening = attr.attr(default=False, init=False)
    client_sockets = attr.attr(default=attr.Factory(dict))
    client_threads = attr.attr(default=attr.Factory(dict))
    uid = attr.attr(default=attr.Factory(uuid.uuid4))

    @staticmethod
    def add_cxn_user(cxn_id, user_obj):
        pass

    @staticmethod
    def add_tunnel_user(tun_id, user_obj):
        NetConnection.net_cxn_lock.acquire()
        existing_users = NetConnection.existing_tunnel_users.get(tun_id, list())
        if user_obj not in existing_users:
            existing_users.append(user_obj)
        NetConnection.existing_tunnel_users[tun_id] = existing_users
        NetConnection.net_cxn_lock.release()
        #NetConnection.existing_tunnel_users[tun_id] = NetConnection.existing_tunnel_users.get(tun_id, list()).append(obj)

    @staticmethod
    def reset_connections():
        [nc.close() for nc in NetConnection.existing_cxn_map.values()]

    @staticmethod
    def stateless_connection_test(host, port):
        try:
            NetCore.build_listen_socket(host=host, port=port)
        except:
            print("Connection test on %s:%s failed" % (host, port))
            raise

    def set_socket(self, socket):
        self.socket = socket
        return self

    def connect_existing_socket(self, socket):
        host, port = self.get_host_port()

        try:
            socket.connect((host, port))
        except ConnectionRefusedError as e:
            print("Unable to connect to %s:%s" % (host, port))
            raise
        self.set_socket(socket=socket)

    def host_is_localhost(self):
        return self.host in ('127.0.0.1', 'localhost', '::1')

    def tunnel_config_applies(self):
        if conf.tunnel:
            do_tun = ((not self.host_is_localhost())
                      or (self.host_is_localhost()
                          and conf.tunnel_for_local_connections))
        else:
            do_tun = False
        return do_tun

    def get_id(self):
        return "%s-%s-%s" % (self.host, self.port, self.uid)

    def register_this_connection(self):
        id = self.get_id()
        NetConnection.net_cxn_lock.acquire()
        if id in NetConnection.existing_cxn_map:
            raise ValueError("Cxn id %s exists in map"%id)
        NetConnection.existing_cxn_map[self.get_id()] = self
        NetConnection.net_cxn_lock.release()

    def connect(self):
        #self.host = host if host is not None else self.host
        #self.port = port if port is not None else self.port
        if self.is_listening:
            raise ValueError("Can't connect with a listening connection")

        if self.is_connected:
            return self

        if self.tunnel_config_applies():
            self.open_tunnel()

        #self.socket = NetConnection.existing_cxn_map.get(self.get_id())
        if self.socket is None:
            self.socket = NetCore.build_socket()
            self.socket.connect((self.host if self.host is not None else '',
                                 self.port))
        self.host, self.port = self.socket.getsockname()
        self.is_connected = True
        return self

    def serial_accept(self, callback):
        self.check_socket()
        while self.is_listening:
            try:
                client_sock, addr = self.socket.accept()
            except socket.timeout as e:
                continue

            cxn = NetConnection(self.host, self.port).set_socket(client_sock)
            callback(cxn)
        self.socket.close()
        self.socket = None

    def thread_accept(self, callback):
        self.check_socket()
        while self.is_listening:
            try:
                client_sock, addr = self.socket.accept()
            except socket.timeout as e:
                continue

            uid = str(uuid.uuid4())
            logger.debug("Launching callback with thread in thread accept")
            self.client_sockets[uid] = NetConnection(self.host, self.port).set_socket(client_sock)
            t = threading.Thread(target=callback, args=[self.client_sockets[uid]])
            t.daemon = True
            t.start()
            self.client_threads[uid] = t
            # Cleanup old threads
            [t.join() for t in self.client_threads.values() if not t.isAlive()]

        self.socket.close()
        self.socket = None

        #for uid, cxn in self.client_sockets.items():
        #    cxn.close()

    def listen(self):
        if self.socket is not None or self.is_listening:
            raise ValueError("Net connection is already listening")

        self.socket = NetCore.build_listen_socket(host=self.host,
                                                  port=self.port,
                                                  timeout=1,
                                                  listen_size=50,
                                                  increment_until_success=True)
        self.is_listening = True
        return self

    def get_host_port(self):
        if self.tunnel is not None:
            host_port = ('127.0.0.1',
                         self.tunnel.local_bind_port)
        else:
            if self.socket is None:
                raise ValueError("Non existent socket has no port and host")
            self.host, self.port = self.socket.getsockname()
            host_port = self.host, self.port
        return host_port

    def open_tunnel(self, user=None, password=None, ssh_port=22):
        """Create a local port that is forwarded to this host:port"""
        if self.host is None and self.port is None:
            raise ValueError("NetConnection must have a host and port ot tunnel to")

        if user is None and conf.default_ssh_user is None:
            user = input("Enter SSH user for {h}:".format(h=self.host))
        elif user is None:
            user = conf.default_ssh_user

        if user in NetConnection.pw_cache:
            password = NetConnection.pw_cache[user]
        elif password is None and conf.default_ssh_password is None:
            password = getpass("Enter SSH Password for {u}@{h}:".format(u=user, h=self.host))
        elif password is None:
            password = conf.default_ssh_password

        tun_key = "%s:%s-to-%s" % (self.host, ssh_port, self.port)
        self.tunnel = NetConnection.existing_tunnel_map.get(tun_key, None)
        if self.tunnel is None:
            self.tunnel = tunnel_to(ssh_host=self.host,
                                    ssh_port=ssh_port,
                                    remote_bind_port=self.port,
                                    user=user, password=password)
        NetConnection.add_tunnel_user(tun_key, self)

    def close(self):
        # TODO: This should remove connections and tunnels
        # from the registry dictionaries if it is the last user
        #raise NotImplementedError("Net connection can't close :(")
        if self.is_listening:
            self.is_listening = False
        elif self.is_connected:
            self.is_connected = False
            self.socket.close()
            self.socket = None

    def check_socket(self):
        if self.socket is None:
            raise ValueError("Can't send, socket not connected")

    def send(self, obj):
        self.check_socket()
        return NetCore.send_object(self.socket, obj)

    def receive(self):
        self.check_socket()
        return NetCore.receive_object(self.socket)

    def send_then_receive(self, obj):
        self.check_socket()
        return NetCore.send_then_receive_response(self.socket,
                                                  obj)


@attr.attributes
class NetBroadcast(object):
    # Map host/ports/service to existing sockets/tunnel
    existing_cxn_map = dict()

    # Map host/ports/service to objects using it
    existing_cxn_users = dict()

    callback = attr.attr(default=None, init=True)
    port = attr.attr(default=BROADCAST_PORT, init=True)
    stop_event = attr.attr(default=attr.Factory(threading.Event), init=False)
    broadcast_listen_thread = attr.attr(default=None, init=False)


    broadcast_socket = attr.attr(default=None)
    received_data = attr.attr(default=attr.Factory(Queue))
    uuid = attr.attr(default=attr.Factory(uuid.uuid4))

    finished = attr.attr(default=False)
    listen_socket = attr.attr(default=None)
    broadcast_socket = attr.attr(default=None)

    def get_id(self):
        return "%s--%s" % (self.uuid, self.port)

    def listen_for_broadcasts(self, callback, endless=True, timeout=4):
        if self.listen_socket is None:
            self.listen_socket = BroadcastCore.build_listen_socket(port=self.port, timeout=2)

        self.stop_event.clear()

        while not self.stop_event.is_set() and not self.finished:
            print("Listening for broadcasts!")
            data, addr = BroadcastCore.listen_for_broadcasts(sock=self.listen_socket, timeout=timeout,
                                                             callback=callback,
                                                             size=128, stop_event=self.stop_event)
            if data is not None:
                print("Got brodcast data: %s" % str(data))
                #callback(addr, data, self.stop_event)
                self.received_data.put((data, addr))
            else:
                print("NO data")

            if self.stop_event.is_set() and endless:
                self.stop_event.clear()

    def launch_broadcast_listener(self):
        if self.broadcast_listen_thread is not None:
            raise ValueError("Broadcast listener already running!")

        t = threading.Thread(target=self.listen_for_broadcasts,
                             args=[self.callback, True])
        #args = [self.port, callback, 64, 3, self.socket, False, self.stop_event]
        #t = threading.Thread(target=BroadcastCore.listen_for_broadcasts,
        #                     args=args)
        t.daemon = True
        t.start()
        self.broadcast_listen_thread = t
        return self

    def broadcast(self, obj, ttl=1):
        if self.broadcast_socket is None:
            self.broadcast_socket = BroadcastCore.build_broadcast_socket(ttl=ttl)
        return BroadcastCore.send_broadcast(obj, self.broadcast_socket)

    def broadcast_then_receive(self, obj):
        if self.broadcast_socket is None:
            self.broadcast_socket = BroadcastCore.build_broadcast_socket(ttl=1)

        if self.listen_socket is None:
            self.listen_socket = BroadcastCore.build_listen_socket(port=self.port, timeout=2)

        return BroadcastCore.bcast_and_recv_responses(obj,
                                                      listen_socket=self.listen_socket,
                                                      broadcast_socket=self.broadcast_socket,
                                                      max_responses=100,
                                                      timeout=2)

    def close(self):
        self.stop_event.set()
        self.finished = True
        if self.broadcast_socket is not None:
            self.broadcast_socket.close()
            self.broadcast_socket = None

        if self.listen_socket is not None:
            self.listen_socket.close()
            self.listen_socket = None

        if self.broadcast_listen_thread is not None:
            self.broadcast_listen_thread.join()


