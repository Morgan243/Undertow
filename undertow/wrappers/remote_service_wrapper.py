import attr
import uuid
from undertow.net_core.bsd_socket import NetCore
from undertow.net_core.net_connection import NetConnection, NetBroadcast
from undertow.wrappers.remote_output_wrapper import RemoteOutputWrapper
from undertow.wrappers.callback_wrapper import CallbackWrapper
from undertow.net_core.undertow_protocol import UndertowBroadcastProtocol
from undertow import utils, configuration
import functools

logger = utils.setup_logger(name='service')

@attr.attributes
class RemoteServiceWrapper(object):
    instance_id = attr.attr(default=attr.Factory(uuid.uuid4), init=True)
    name = attr.attr(default=None, init=True)
    id = attr.attr(default=None, init=True)
    host = attr.attr(default=None, init=True)
    port = attr.attr(default=None, init=True)
    callback_map = attr.attr(default=None, init=True)
    net_connection = attr.attr(default=None, init=False)

    @staticmethod
    def broadcast_for_service(name, ut_id=None, return_first=True):
        responses = NetBroadcast().broadcast_then_receive(name)
        if len(responses) == 0:
            logger.info("\t[X] No responses for %s" % name)
            return None
        print(responses)
        if return_first:
            return responses[0][1][0], int(responses[0][0].decode('utf-8').split(':')[-1])
        else:
            return set([(r[1][0], int(r[0].decode('utf-8').split(':')[-1])) for r in responses])

        #return UndertowBroadcastProtocol.broadcast_for_service(name=name,
        #                                                       max_to_return=1 if return_first else 100)

    # TODO: Handle connection sharing here?
    def exec_remote_callback(self, *args, #host=None, port=None,
                             cb_func=None, cb_args=None, cb_kwargs=None,
                             meta_data=None, **kwargs):
        if cb_args is None:
            cb_args = list()

        if cb_kwargs is None:
            cb_kwargs = dict()

        if meta_data is None:
            meta_data = dict()

        cb_args += args
        cb_kwargs.update(kwargs)

        cbr = CallbackWrapper.build_callback_request(cb_func, args=cb_args, kwargs=cb_kwargs,
                                                     return_output=True, meta_data=meta_data)

        try:
            #cxn = NetConnection(host=host, port=port).connect()
            cxn = NetConnection(host=self.host, port=self.port).connect()
            response = cxn.send_then_receive(cbr)
            cxn.close()
        except:
            raise

        return response

    def connect(self):
        if self.net_connection is None:
            self.net_connection = NetConnection(host=self.host,
                                                port=self.port).connect()

        return self

    def fetch_callbacks(self):
        try:
            resp = self.net_connection.send_then_receive('callbacks')
            #s = NetCore.build_client_socket(self.host, self.port)
            #resp = NetCore.send_then_receive_response(s, 'callbacks')
        except:
            raise
        self.callback_map = resp
        return self

    def run(self, *args, cb_name='none', return_value_only=True, **kwargs):

        #resp = self.net_connection.send_then_receive('callbacks')

        res = self.exec_remote_callback(cb_func=cb_name,
                                        cb_args=args,
                                        cb_kwargs=kwargs)

        #res = NetCore.exec_remote_callback(host=self.host,
        #                                   port=self.port,
        #                                   cb_func=cb_name,
        #                                   cb_args=args, cb_kwargs=kwargs)
        if return_value_only:
            ro = res
        else:
            ro = RemoteOutputWrapper().remote_output(service=self,
                                                     output=res)
        return ro

    @staticmethod
    def remote_service(host, port, name='unknown', callbacks=None,
                       worker_map=None, add_connect_test=True,
                       except_on_ping_fail=True):
        #if (not configuration.tunnel_for_local_connections
        #    and configuration.default_tunnel == 'ssh'):
        if configuration.redirect_to_local_host:
            if host in NetCore.get_net_address(return_one=False):
                host = '127.0.0.1'
        id = uuid.uuid4()
        rs = RemoteServiceWrapper(name=name, id=id,
                                  host=host, port=port)
                                  #instance_id=ServiceModule.get_friendly_name())
        ping_success = rs.UNDERTOW_PING()
        if not ping_success and except_on_ping_fail:
            raise ValueError("Unable to ping %s on %s:%s" % (name, host, port))
        elif not ping_success:
            return None

        if callbacks is None:
            callbacks = rs.fetch_callbacks().callback_map

        for f_name in callbacks:
            f = functools.partial(rs.run, cb_name=f_name,
                                  return_value_only=True)
            setattr(rs, f_name, f)

        if add_connect_test:
            f = functools.partial(NetConnection.stateless_connection_test,#NetCore.build_client_socket,
                                  host=host, port=port)
            setattr(rs, 'connect_test', f)
        return rs

    def UNDERTOW_PING(self):
        try:
            #cxn = NetConnection(host=self.host, port=self.port).connect()
            self.connect()
            resp = self.net_connection.send_then_receive('ping')

            #s = NetCore.build_client_socket(self.host, self.port)
            #resp = NetCore.send_then_receive_response(s, 'ping')
        except:
            raise
            #return False

        if resp != 'pong':
            raise ValueError("Invalid ping response %s" % str(resp))
        return True

