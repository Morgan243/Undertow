import time
import socket
import attr
import uuid
try:
    from queue import Queue
except ImportError as e:
    from Queue import Queue

from threading import Lock, Event
from undertow.net_core.bsd_socket import NetCore, BroadcastCore
from undertow.net_core.net_connection import NetBroadcast
from undertow import utils
from undertow.net_core.net_ptr import NetPtr
from multiprocessing import Pool, Process

thread = utils.thread
logger = utils.setup_logger(name='service')

@attr.attributes
class ServiceInstanceWrapper(object):
    name = attr.attr(default=None, init=True)
    net_connection = attr.attr(default=None, init=True)
    callbacks = attr.attr(default=None, init=True)
    workers = attr.attr(default=None, init=True)

    net_broadcast = attr.attr(default=None, init=False)

    callback_worker_thread = attr.attr(default=None, init=False)
    callback_request_q = attr.attr(default=attr.Factory(Queue), init=False)
    outgoing_q = attr.attr(default=attr.Factory(Queue), init=False)

    client_conn_lock = attr.attr(default=attr.Factory(Lock), init=False)
    client_connections = attr.attr(default=attr.Factory(dict), init=False)

    ptrs_lock = attr.attr(default=attr.Factory(Lock), init=False)
    active_net_ptrs = attr.attr(default=attr.Factory(dict), init=False)

    reg = attr.attr(default=None, init=False)
    uid = attr.attr(default=attr.Factory(uuid.uuid4), init=False)
    remote_registery = attr.attr(default=None)

    num_broadcasts = attr.attr(default=0, init=True)
    l_bcast_recv_sock = attr.attr(default=None, init=True)
    l_bcast_send_sock = attr.attr(default=None, init=True)
    bcast_reponse_thread = attr.attr(default=None, init=False)
    bcast_stop_event = attr.attr(default=None, init=False)

    is_available = attr.attr(default=False, init=False)
    listen_thread = attr.attr(default=None, init=False)
    listen_process = attr.attr(default=None, init=False)
    stop_callbacks = attr.attr(default=attr.Factory(Event))

    def is_running(self):
        return self.listen_process is not None or self.listen_thread is not None

    def set_net_prt(self, ptr):
        self.ptrs_lock.acquire()
        self.active_net_ptrs[ptr.uid] = ptr
        self.ptrs_lock.release()

    def get_net_prt(self, id):
        self.ptrs_lock.acquire()
        ptr = self.active_net_ptrs[id]
        self.ptrs_lock.release()
        return ptr

    def delete_net_prt(self, id):
        self.ptrs_lock.acquire()
        del self.active_net_ptrs[id]
        self.ptrs_lock.release()

    def register(self, reg):
        if not self.is_available:
            raise ValueError("Cannot register a service that is not available")
        # May want to register workers too?
        self.remote_registery = reg
        logger.info("Register is %s" % str(self.remote_registery))
        logger.info("Callbacks: %s" % str(self.callbacks))

        h, p = self.net_connection.get_host_port()
        self.remote_registery.add_to_register(host=h, port=p,#NetCore.get_net_address(),
                                              service_name=self.name,
                                              callbacks=list(self.callbacks.callback_map.keys()))

        return self

    def wait_on_workers(self, timeout=None):
        [wrk.wait_on(timeout=timeout) for wrk in self.workers]
        return self

    def create_bcast_data(self):
        #bcast_data = "%s:[%s]" % (self.name,
        #                             self.uid)

        host, port = self.net_connection.get_host_port()
        bcast_data = "%s:[%s]:%d" % (self.name,
                                     self.uid,
                                     port)
        return bcast_data, bytes(bcast_data, encoding='utf-8')

    def broadcast_service(self):
        bcast_data, bcast_data_utf8 = self.create_bcast_data()
        BroadcastCore.send_broadcast(bcast_data_utf8,
                                     sock=self.l_bcast_send_sock)
        self.num_broadcasts += 1

    def respond_to_broadcast(self, addr, data, stop_event):
        data = data.decode("utf-8")
        if self.net_broadcast.broadcast_socket is not None:
            send_sock = self.net_broadcast.broadcast_socket.getsockname()[1]
        else:
            send_sock = None

        bcast_data, bcast_data_utf8 = self.create_bcast_data()

        if bcast_data == data and addr[1] == send_sock:
            #logger.debug("Saw broadcast from self: %s" % str(data))
            return
        if str(data) != self.name:
            logger.debug("Saw broadcast for different service: %s" % str(data))
            return

        logger.debug("Broadcast looking for this service! (%s)" % str(self.name))
        logger.debug("Responding to broadcast (%d)" % self.num_broadcasts)
        logger.debug("\t%s - %s" % (str(addr), str(data)))
        logger.debug("\t%s" % str(bcast_data))
        self.broadcast_service()
        # If we indicate a stop, then it will only respond to one broadcast then close
        #stop_event.set()
        #return False

    def enable_broadcast_response(self):
        if self.net_broadcast is None:
            self.net_broadcast = NetBroadcast(callback=self.respond_to_broadcast)
            self.net_broadcast.launch_broadcast_listener()
        return self

    def callback_worker(self):
        """
        Pops (Connections, NetPtr) tuples from the callback queue and performs the call
        in a blocking manner. The result of the callback is assigned back to the NetPtr's
        object.
        :param callbacks:
        :param pass_connection_list:
        :param origin_listen_port:
        :return:
        """

        #while not stop_event.isSet():
        while not self.stop_callbacks.isSet():
            cxn, ptr = self.callback_request_q.get(block=True)
            #obj = ptr.callback_request_dict


            ptr.run_callback_request()
            #logger.debug("%s finished after %.3f seconds" % (obj['call_name'], delta_t))
        print("handle_clients_callback listener is exiting")
        logger.debug("handle_clients_callback listener is exiting")

    def handle_client(self, cxn):
        while not self.stop_callbacks.isSet():
            try:
                obj = cxn.receive()
                logger.debug("Received: %s" % str(obj))
                if obj is not None and isinstance(obj, dict):
                    callback_func = self.callbacks.get_callback_func(obj['call_name'])
                    callback_args = obj['args']
                    callback_kwargs = obj['kwargs']
                    return_output = obj['return_output']
                    container_type = self.callbacks.get_callback_container(obj['call_name'])
                    ptr = NetPtr(callback_func=callback_func,
                                 callback_args=callback_args,
                                 callback_kwargs=callback_kwargs,
                                 return_output=return_output,
                                 container_type=container_type)

                    # run callback directly
                    self.set_net_prt(ptr)
                    self.callback_request_q.put((cxn, ptr))
                    res = ptr.get()
                    try:
                        cxn.send(res)
                        # Don't let return objects pile up!
                        self.delete_net_prt(ptr.uid)
                        del ptr
                        del obj
                    except TypeError as e:
                        print("Handle client send obj type error!!")

                # Got net pointer, so send our copy back
                elif obj is not None and isinstance(obj, NetPtr):
                    print("WARNING: NetPtr usage!")
                    #ptr = UndertowProtocol.client_net_ptrs[l_port][obj.uid]
                    ptr = self.get_net_prt(obj.uid)
                    if obj.block:
                        cxn.send(ptr.wait_on())
                    else:
                        cxn.send(ptr)

                    self.delete_net_prt(obj.uid)
                    del ptr
                elif obj == 'ping':
                    cxn.send('pong')
                elif obj == 'callbacks':
                    cxn.send(list(self.callbacks.callback_map.keys()))
                else:
                    break
            # This is usually client went away?
            except EOFError as e:
                break
            except TypeError as e:
                raise
            except:
                raise

    def __start(self):
        if self.net_connection is None:
            raise ValueError("No net connection for service instance")
        self.net_connection.listen()

        self.listen_thread = utils.thread(target=self.net_connection.thread_accept,
                                          kwargs=dict(callback=self.handle_client))

        self.callback_worker_thread = utils.thread(target=self.callback_worker)

        self.is_available = True
        logger.debug("%s has been made available" % str(self.name))
        return self

    def __start_as_process(self):
        raise NotImplementedError()


    def make_available(self, as_process=False, blocking=False):
        if self.is_running():
            raise ValueError("Cant call make_available when already available")

        if as_process:
            raise NotImplementedError("Can't start process in another process automagically")
            # Process won't share data with current process, will cause
            # problems if some things become state-dependent....
            logger.debug("Making available as process")
            self.listen_process = Process(target=self.__start_as_process)
            self.listen_process.start()
        else:
            self.__start()

        if blocking:
            self.wait_on()

        return self




    def wait_on(self):
        if self.listen_thread is not None:
            self.listen_thread.join()
        elif self.listen_process is not None:
            self.listen_process.join()

        self.wait_on_workers()
        #self.callbacks.wait_on()
        #self.done_event.wait()

        #self.l_sock = None
        self.listen_thread = None
        self.listen_process = None

    def stop(self, block=True):
        self.close(block=True)

    def close(self, block=True):
        print("Closing callbacks...")
        self.stop_callbacks.set()
        if self.net_connection is not None:
            self.net_connection.close()
        if self.net_broadcast is not None:
            self.net_broadcast.close()

        if block:
            self.wait_on()

        logger.info("Service %s stopped" % str(self.name))
        return self
        #for available_callbacks[self.name]
        #del available_callbacks[self.uid]
        #self.listen_thread.join()
        #self.l_sock.close()


    def __enter__(self):
        return self

    def __exit__(self, except_type, except_value, traceback):
        self.stop()
