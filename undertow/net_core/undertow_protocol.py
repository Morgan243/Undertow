from undertow.net_core.ssh_tunnel import tunnel_to
from undertow.net_core.bsd_socket import NetCore
from undertow.net_core.net_ptr import NetPtr
from undertow import configuration  as conf
from undertow.net_core.net_connection import NetConnection, BroadcastCore
import undertow.utils as utils
import socket
import attr

thread = utils.thread
logger = utils.setup_logger(name='service')



@attr.attributes
class UndertowProtocol(object):

    service_connections = attr.attr(default=None)
    client_net_ptrs = dict()

    # TODO: Put these back in net connection
    # TODO: Place here get callbacks, discover, use registry
    @staticmethod
    def callback_listener(cb_wrapper):
        #print("Call back listener started")

        thread_kwargs = dict(stop_event=cb_wrapper.stop_callbacks,
                             origin_listen_port=cb_wrapper.l_port)
        callback_thread = thread(target=UndertowProtocol.callback_worker,
                                 kwargs=thread_kwargs,
                                 name='Callback worker')
        listening_threads, dead_threads = list(), list()
        while not cb_wrapper.stop_callbacks.isSet():
            try:
                conn, add = cb_wrapper.l_sock.accept()
                if cb_wrapper.on_connect is not None:
                    cb_wrapper.on_connect()

                targs = [conn, cb_wrapper]
                if len(cb_wrapper.callback_map) > 0:
                    t = thread(target=UndertowProtocol.handle_client,
                               args=targs)
                    listening_threads.append(t)

                dead_threads = [lt for lt in listening_threads
                                if not lt.isAlive()]
                listening_threads = [lt for lt in listening_threads
                                     if lt.isAlive()]

                [dt.join() for dt in dead_threads]
            except socket.timeout as e:
                continue
            # When connection breaks
            except OSError as e:
                cb_wrapper.l_sock.close()
                break
            except:
                raise
                break


    @staticmethod
    def callback_worker(stop_event, pass_connection_list=None,
                        origin_listen_port=None):
        """
        Pops (Connections, NetPtr) tuples from the callback queue and performs the call
        in a blocking manner. The result of the callback is assigned back to the NetPtr's
        object.
        :param callbacks:
        :param pass_connection_list:
        :param origin_listen_port:
        :return:
        """

        if pass_connection_list is None:
            pass_connection_list = list()

        while not stop_event.isSet():
            conn, ptr = callback_q.get(block=True)
            obj = ptr.callback_request_dict
            l_port = ptr.port

            if isinstance(obj, dict):
                # If this had the net_async kwargs set, go ahead and remove it
                # in order to not pass it to the callback
                if 'net_async' in obj['kwargs'] and obj['kwargs']['net_async']:
                    del obj['kwargs']['net_async']

                t1 = time.time()

                # Does this method require the connection object be passed to it?
                if obj['call_name'] in pass_connection_list:
                    # TODO: can't send back (can't pickle) the socket
                    # ptr.callback_request_dict['kwargs']['conn'] = conn
                    pass

                ptr.set_obj(ptr.run_callback_request())
                t2 = time.time()
                delta_t = t2 - t1
                if delta_t > 2:
                    logger.debug("%s finished after %.3f seconds" % (obj['call_name'], delta_t))
            else:
                pass
        print("handle_clients_callback listener is exiting")
        logger.debug("handle_clients_callback listener is exiting")

    @staticmethod
    def handle_client(conn, cb_container):
        l_port = conn.getsockname()[1]

        if l_port not in UndertowProtocol.client_net_ptrs:
            UndertowProtocol.client_ptr_buckets[l_port] = dict()

        while True:
            try:
                obj = NetCore.receive_object(conn)
                if obj is not None and isinstance(obj, dict):
                    ptr = NetPtr(cb_container=cb_container,
                                 callback_request_dict=obj)

                    if 'net_async' in obj['kwargs'] and obj['kwargs']['net_async']:
                        # Send back a reference to the callbacks return
                        print("WARNING: ASYNC SEND!!")
                        NetCore.send_object(conn, ptr)
                        UndertowProtocol.client_net_ptrs[l_port][ptr.obj_id] = ptr
                        callback_q.put((conn, ptr))
                        del obj['kwargs']['net_async']
                    else:
                        # run callback directly
                        UndertowProtocol.client_ptr_buckets[l_port][ptr.obj_id] = ptr
                        callback_q.put((conn, ptr))
                        res = ptr.get()
                        # print("returning %s" % str(type(res)))
                        try:
                            NetCore.send_object(conn, res)
                            # Don't let return objects pile up!
                            del UndertowProtocol.client_net_ptrs[l_port][ptr.obj_id]
                            del ptr
                            del obj
                        except TypeError as e:
                            print("Handle client send obj type error!!")

                # Got net pointer, so send our copy back
                elif obj is not None and isinstance(obj, NetPtr):
                    print("WARNING: NetPtr usage!")
                    ptr = UndertowProtocol.client_net_ptrs[l_port][obj.obj_id]
                    if obj.block:
                        NetCore.send_object(conn, ptr.wait_on())
                    else:
                        NetCore.send_object(conn, ptr)

                    del UndertowProtocol.client_net_ptrs[l_port][obj.obj_id]
                    del ptr
                elif obj == 'ping':
                    # print("Got ping!")
                    NetCore.send_object(conn, 'pong')
                elif obj == 'callbacks':
                    NetCore.send_object(conn, list(cb_container.callback_map.keys()))
                else:
                    break
            # This is usually client went away?
            except EOFError as e:
                break
            except TypeError as e:
                raise
            except:
                raise




@attr.attributes
class UndertowBroadcastProtocol(object):
    @staticmethod
    def broadcast_for_service(name, ut_id=None, max_to_return=1):
        #logger.info("Broadcasting for %s" % name)
        responses = BroadcastCore.bcast_and_recv_responses(name)
        if len(responses) == 0:
            logger.info("\t [X] Found no %s" % name)
            return None

        print(responses)
        if max_to_return == 1:
            return responses[0][1][0], int(responses[0][0].decode('utf-8').split(':')[-1])
        else:
            return set([(r[1][0], int(r[0].decode('utf-8').split(':')[-1])) for r in responses])




