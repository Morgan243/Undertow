import importlib
import sys
import os
import time
import importlib
import argparse
import functools
import inspect
import random
import threading
import uuid
import attr

from undertow import utils
from undertow.net_core.bsd_socket import BroadcastCore
from undertow.net_core.bsd_socket import NetCore
from undertow.net_core.net_connection import NetConnection

from undertow.wrappers.callback_wrapper import CallbackWrapper, available_callbacks
from undertow.wrappers.worker_wrapper import WorkerWrapper
from undertow.wrappers.service_instance_wrapper import ServiceInstanceWrapper
from undertow.wrappers.remote_service_wrapper import RemoteServiceWrapper
from undertow.wrappers.multi_remote_service_wrapper import MultiRemoteServiceWrapper
from undertow.net_core.undertow_protocol import UndertowProtocol, UndertowBroadcastProtocol

logger = utils.setup_logger(name='service')


class Expose(object):
    def __init__(self, name=None, container_type=None):
        self.name = name
        self.container_type = container_type

    def __call__(self, obj):
        ServiceModule.expose(obj, self.name, self.container_type)
        return obj


class Worker(Expose):
    def __call__(self, obj):
        return ServiceModule.worker(obj, self.name)


@attr.attributes
class ServiceModule(object):
    default_port = 2438
    alias_to_entity_id = dict()

    ##########
    # Helpers
    @staticmethod
    def get_friendly_name():
        try:
            path = '/home/morgan/Projects/Crawler/repute/data/names.txt'
            names = open(path, 'r').readlines()
        except:
            names = ["bill", "bob", "ann", "rachel", "archer",
                     "ringo", "dingo", "boro", "bro"]
        idx = random.randint(0, len(names)-1)
        tmp_name = names[idx].strip()
        return tmp_name[0] + tmp_name[1:].lower()

    @staticmethod
    def ambig_class_id(id):
        if inspect.isclass(id):
            cls_name = str(id.__class__.__name__)
        elif isinstance(id, str):
            cls_name = id
        else:
            raise ValueError("Dont know waht to do with %s" % id)
        return cls_name

    ####################
    ## Attr manipulation
    @staticmethod
    #def assign_undertow_properties(obj, ut_type, alias, in_subprocess=False):
    def assign_undertow_properties(obj, ut_type, alias, container_type=None):
        if hasattr(obj, 'UNDERTOW'):
            raise ValueError("Object %s already has UNDERTOW attr" % str(obj))
        if container_type is None:
            container_type = 'thread'

        obj.UNDERTOW = dict()
        obj.UNDERTOW['ID'] = uuid.uuid4()
        obj.UNDERTOW['TYPE'] = ut_type
        obj.UNDERTOW['ALIAS'] = alias
        #obj.UNDERTOW['IN_SUBPROCESS'] = in_subprocess
        obj.UNDERTOW['CONTAINER_TYPE'] = container_type

        return obj

    @staticmethod
    def get_undertow_id(obj):
        return ServiceModule.get_undertow_property_value(obj, 'ID', None)

    @staticmethod
    def get_undertow_type(obj):
        return ServiceModule.get_undertow_property_value(obj, 'TYPE', None)

    @staticmethod
    def get_undertow_alias(obj):
        return ServiceModule.get_undertow_property_value(obj, 'ALIAS', None)

    @staticmethod
    def get_undertow_in_subprocess(obj):
        return ServiceModule.get_undertow_property_value(obj, 'IN_SUBPROCESS', False)

    @staticmethod
    def get_undertow_container_type(obj):
        return ServiceModule.get_undertow_property_value(obj, 'CONTAINER_TYPE', False)

    @staticmethod
    def get_undertow_property_value(obj, prop_key, default=None):
        return getattr(obj, 'UNDERTOW', dict()).get(prop_key, default)

    @staticmethod
    def get_undertow_maps_of_instance(obj):
        callbacks = dict()
        callback_container = dict()
        workers = dict()
        worker_container = dict()
        in_subprocess = list()
        for prop_name in dir(obj):
            prop = getattr(obj, prop_name)
            ut_id = ServiceModule.get_undertow_id(prop)
            ut_type = ServiceModule.get_undertow_type(prop)
            cont_type = ServiceModule.get_undertow_container_type(prop)
            if ut_id is not None and callable(prop):
                if ut_type == 'callback':
                    callbacks[prop_name] = prop
                    callback_container[prop_name] = cont_type
                if ut_type == 'worker':
                    workers[prop_name] = WorkerWrapper.worker(prop,
                                                              container_type=cont_type)
                    #workers[prop_name] = prop
                    #worker_container[prop_name] = cont_type

        print("CB CONTAINER FOR %s" % str(ServiceModule.get_undertow_alias(obj)))
        cb_container = CallbackWrapper.callbacks(name=ServiceModule.get_undertow_alias(obj),
                                                 callback_map=callbacks,
                                                 container_map=callback_container)
        return cb_container, workers
        #cb_container.make_available(host=host, port=port)
        #return callbacks, workers, in_subprocess


    ################
    ## Remote aspects
    @staticmethod
    def remote_service(host, port, name='unknown', callbacks=None,
                       worker_map=None, add_connect_test=True,
                       except_on_ping_fail=True):
        id = uuid.uuid4()
        rs = RemoteServiceWrapper(name=name, id=id,
                                  host=host, port=port,
                                  instance_id=ServiceModule.get_friendly_name())
        rs.connect()
        ping_success = rs.UNDERTOW_PING()
        if not ping_success and except_on_ping_fail:
            raise ValueError("Unable to ping %s on %s:%s" % (name, host, port))
        elif not ping_success:
            return None

        if callbacks is None:
            callbacks = rs.fetch_callbacks().callback_map

        for f_name in callbacks:
            f = functools.partial(rs.exec_remote_callback,#UndertowProtocol.exec_remote_callback,#NetCore.exec_remote_callback,
                                  cb_func=f_name)
            setattr(rs, f_name, f)

        if add_connect_test:
            #f = functools.partial(NetCore.build_client_socket,
            #                      host=host, port=port)
            f = functools.partial(NetConnection.stateless_connection_test,
                                  host=host, port=port)
            setattr(rs, 'connect_test', f)
        return rs

#    @staticmethod
#    def broadcast_for_service(obj, return_first=True):
#        ut_id = ServiceModule.get_undertow_id(obj)
#        name = ServiceModule.get_undertow_alias(obj)
#        return RemoteServiceWrapper.broadcast_for_service(name=name,
#                                                          return_first=return_first)

        #logger.info("Broadcasting for %s" % name)
        #responses = BroadcastCore.bcast_and_recv_responses(name)
        #if len(responses) == 0:
        #    logger.info("\t [X] Found no %s" % name)
        #    return None

        #print(responses)
        #if return_first:
        #    return responses[0][1][0], int(responses[0][0].decode('utf-8').split(':')[-1])
        #else:
        #    return set([(r[1][0], int(r[0].decode('utf-8').split(':')[-1])) for r in responses])

    @staticmethod
    def discover(obj, return_one=True):
        name = ServiceModule.get_undertow_alias(obj)
        host_ports = RemoteServiceWrapper.broadcast_for_service(name=name,
                                                                return_first=False)
        #host_ports = ServiceModule.broadcast_for_service(obj,
        #                                                 return_first=False)
        logger.info("DISCOVERED: %s" % str(host_ports))
        if host_ports is None:
            return None
        remotes = [RemoteServiceWrapper.remote_service(name=name,
                                        host=host, port=port).connect().fetch_callbacks()
                   for host, port in host_ports]

        #remotes = [RemoteServiceWrapper.remote_service(name=name,
        #                                               host=host, port=port,
        #                                               except_on_ping_fail=False)
        #           for host, port in host_ports]
        #remotes = [rs.fetch_callbacks() for rs in remotes if rs is not None]

        if len(remotes) == 0:
            raise ValueError("No remote for %s found" % name)
        elif return_one:
            return remotes[0]
        else:
            return MultiRemoteServiceWrapper().multi_remote_service(remotes)

    @staticmethod
    def remote_service_from_registry(name, remote_reg=None, return_one=True):
        from undertow.registry import discover_registry
        if remote_reg is None:
            remote_reg = discover_registry()
        host_info = remote_reg.get_hosts_of_service(name)
        print("Got this from registry: %s" % str(host_info))
        all_rs = list()
        for prop in host_info:
            try:
                host, port = prop['host_tuple']
                rs = RemoteServiceWrapper.remote_service(host=host, port=port, name=name)
                if return_one:
                    return rs
                else:
                    all_rs.append(rs)
            except:
                raise
        return MultiRemoteServiceWrapper().multi_remote_service(all_rs)

    ###############
    # Launching
    @staticmethod
    def launch_workers(obj, *args, **kwargs):
        cb_container, workers = ServiceModule.get_undertow_maps_of_instance(obj)

        for name, wrk_container in workers.items():
            # TODO: why do this way?
            wrk_container.wrk_args = args
            wrk_container.wrk_kwargs = kwargs
            wrk_container.launch()
        #for name, wrk_func in workers.items():
        #    wrk = WorkerWrapper.worker(wrk_func, wrk_args=args,
        #                               wrk_kwargs=kwargs, launch=True)

    @staticmethod
    def launch(obj, host=None, port=None, net_connection=None,
               name=None, reg=None,
               as_process=False,
               bcast_response=True,
               blocking=False):

        cb_container, workers = ServiceModule.get_undertow_maps_of_instance(obj)

        if name is None:
            name = ServiceModule.get_undertow_alias(obj)

        if net_connection is None:
            net_connection = NetConnection(host=host, port=port)

        #logger.info("%s callbacks on port %s" % (str(obj),
        #                                          cb_container.l_port))

        # TODO: launch workers in separate process if the
        # worker func name is in 'in_subproc' list
        workers = [WorkerWrapper.worker(wrk_func, launch=True)
                   for _name, wrk_func in workers.items()]
        [w.launch() for w in workers]

        ls = ServiceInstanceWrapper(name=name,
                                    callbacks=cb_container,
                                    workers=workers,
                                    net_connection=net_connection)

        if bcast_response:
            logger.debug("Launching broadcast responder")
            ls.enable_broadcast_response()

        ls.make_available(as_process=as_process)

        if reg is not None:
            ls.register(reg)

        if blocking:
            ls.wait_on()

        return ls


    #############
    ## Decorating
    @staticmethod
    def decorate_class(cls, name=None):
        if name is None:
            name = str(cls.__class__.name)

        cls_obj = ServiceModule.assign_undertow_properties(cls, 'class',
                                                           alias=name)
        ServiceModule.alias_to_entity_id[name] = ServiceModule.get_undertow_id(cls_obj)

        return cls_obj

    @staticmethod
    def decorate_method(func, name=None, in_subprocess=False, container_type=None):
        if name is None:
            name = func.__name__

        func_obj = ServiceModule.assign_undertow_properties(func, 'callback',
                                                            alias=name,
                                                            container_type=container_type)

        ServiceModule.alias_to_entity_id[name] = ServiceModule.get_undertow_id(func_obj)

        return func_obj

    @staticmethod
    def worker(func, name=None):
        if name is None:
            name = func.__name__

        func_obj = ServiceModule.assign_undertow_properties(func, 'worker',
                                                            alias=name)

        ut_id = ServiceModule.get_undertow_id(func_obj)
        ServiceModule.alias_to_entity_id[name] = ut_id

        return func

    @staticmethod
    def expose(obj, name=None, container_type=None, persistent=True):

        if name is None:
            name = obj.__name__

        if inspect.isclass(obj):
            d_obj = ServiceModule.decorate_class(obj, name=name)
        elif callable(obj):
            #print("Exposing container: %s" % str(container_type))
            d_obj = ServiceModule.decorate_method(obj, name=name,
                                                  container_type=container_type)
        else:
            raise ValueError("%s given to decorator is not either class or callable")

        return d_obj


    @staticmethod
    def launch_from_module_file(module_path, class_name=None,
                                registry_server=None,
                                append_path=True):
        """

        :param module_path:
        :param num_instances:
        :param registry_server:
        :param append_path: Add modules directory to python path
        :return: a launched service instance
        """
        launched_service = list()

        if append_path:
            base_path = os.path.join(*os.path.split(module_path)[:-1])
            sys.path.insert(0, base_path)
            module_name = os.path.split(module_path)[-1]
            imp_mod = importlib.import_module(module_name.split('.')[0])
        else:
            imp_mod = importlib.import_module(module_path)

        for attr in dir(imp_mod):
            m_attr = getattr(imp_mod, attr)
            ut_id = ServiceModule.get_undertow_id(m_attr)
            if inspect.isclass(m_attr) and ut_id is not None:
                alias = ServiceModule.get_undertow_alias(m_attr)

                # If we are only starting a specific class in the module
                if class_name is not None and class_name == alias:
                    continue
                ls = ServiceModule.launch(m_attr(), reg=registry_server)

                logger.info("Launched %s (%s)" % (alias, str(m_attr)))
                launched_service.append(ls)
        return launched_service

    @staticmethod
    def get_available_callbacks(service_name, return_all=True):
        """
        Use to check if a service_name has already exposed callbacks and
        return that callback wrapper
        :param service_name:
        :param return_all:
        :return:
        """
        if not isinstance(service_name, str):
            service_name = ServiceModule.get_undertow_alias(service_name)

        cbs = list()
        for cuid, cb_wrapper in available_callbacks.items():
            if cb_wrapper.name == service_name:
                cbs.append(cb_wrapper)

        print("Discovered callbacks: %s" % str(cbs))
        if not return_all and len(cbs) > 0:
            cbs = cbs[0]
        elif len(cbs) == 0 and not return_all:
            cbs = None

        return cbs


if __name__ == "__main__":
    from undertow.registry import Registry, launch_registry, discover_registry
    parser = argparse.ArgumentParser()

    parser.add_argument('modules', nargs='?', type=str, default=None)
    parser.add_argument('-R', '--start-registry-server', dest='start_reg_srv',
                        action='store_true', default=False)
    parser.add_argument('-P', '--registry-port', dest='registry_port',
                        type=int, default=12233)
    parser.add_argument('-N', '--num-instances', dest='num_instances',
                        type=int, default=1)
    parser.add_argument('-r', '--registry-server', dest='reg_srv_host_port',
                        type=str, default=None)
    parser.add_argument('-d', '--discover-registry', dest='discover_registry',
                        action='store_true', default=False)

    args = parser.parse_args()
    modules = args.modules
    if not isinstance(modules, list) and modules is not None:
        modules = [modules]

    if args.start_reg_srv:
        reg = launch_registry(port=args.registry_port)
        logger.info("Registry launched on port %d" % args.registry_port)
        reg.wait_on()
    elif modules is not None:
        # Need to drop .py in order to import module
        modules = utils.module_name_from_file_name(modules)
        logger.info("Modules: %s" % str(modules))
        if args.reg_srv_host_port is not None:
            host, port = utils.host_port_from_str(args.reg_srv_host_port)
            reg_srv = RemoteServiceWrapper.remote_service(host=host, port=int(port),
                                                          name='registry')
        elif args.discover_registry:
            logger.info("Discovering registry")
            reg_srv = discover_registry()
            if reg_srv is None:
                logger.info("Tried to discover registry, but none found")
        else:
            reg_srv = None

        launched_service = list()
        mp_pool = None
        for m in modules:
            logger.info("Loading %s" % m)
            if args.num_instances == 1:
                launched_service = ServiceModule.launch_from_module_file(module_path=m,
                                                                         registry_server=reg_srv)
            elif args.num_instances > 1:
                logger.info("Launching proxy for %s instances" % str(m))
                #from undertow.proxy import Proxy
                #prox = ServiceModule.launch(Proxy, reg=reg_srv)
                #prox.launch_local_service(module_path=m, )



        for ls in launched_service:
            ls.wait_on()
    else:
        logger.error("Nothing to do...see usage with --help")

