import uuid
import attr
import threading
from undertow.net_core.bsd_socket import NetCore
from undertow import utils
from undertow.configuration import default_port
from multiprocessing import Pool, Process

logger = utils.setup_logger(name='service')

available_callbacks = dict()

@attr.attributes
class CallbackWrapper(object):
    """
    Holds a collection of callback functiions exposed. Generally,
    all the Exposed methods of an Undertow class
    """
    name = attr.attr(default=None, init=False)

    callback_map = attr.attr(default=None, init=False)
    callback_container_map = attr.attr(default=None, init=False)
    on_connect = attr.attr(default=None, init=False)
    on_disconnect = attr.attr(default=None, init=False)

    uid = attr.attr(default=attr.Factory(uuid.uuid4), init=False)

    def get_callback_func(self, call_name):
        if callable(call_name):
            return call_name
        else:
            return self.callback_map[call_name]

    def get_callback_container(self, call_name):
        return self.callback_container_map[call_name]

    @staticmethod
    def build_callback_request(call_name, args=None, kwargs=None,
                               return_output=True, meta_data=None):
        if args is None:
            args = list()
        if kwargs is None:
            kwargs = dict()
        cbr = dict(call_name=call_name,
                   args=args,
                   kwargs=kwargs,
                   return_output=return_output,
                   metadata=meta_data)
        return cbr

    @staticmethod
    def callbacks(name, callback_map, container_map=None):
        if container_map is None:
            container_map = {k: None for k in callback_map.keys()}

        cb = CallbackWrapper()
        cb.name = name
        cb.callback_map = callback_map
        cb.callback_container_map = container_map
        return cb

