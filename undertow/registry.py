from undertow.service import ServiceModule, Expose, Worker
from undertow.wrappers.remote_service_wrapper import RemoteServiceWrapper
import time
import attr
import uuid

from undertow.utils import setup_logger

logger = setup_logger(name='registry')

def launch_registry(port=None, name='registry'):
    reg = Registry()
    return ServiceModule.launch(reg, port=port, name=name).enable_broadcast_response()

def discover_registry():
    return ServiceModule.discover(Registry, return_one=True)

@Expose('registry')
@attr.attributes
class Registry(object):
    registered_services = attr.attr(default=attr.Factory(dict))
    uid_map = attr.attr(default=attr.Factory(dict))
    last_seen_times = attr.attr(default=attr.Factory(dict))

    def pretty_print_services(self):
        for svc, uids in self.registered_services.items():
            logger.info("%s: %d" % (svc, len(uids)))

    @Expose()
    def remove_from_register(self, uid):
        for svc_name, _uid in self.registered_services.items():
            self.registered_services[svc_name].remove(uid)

        del self.uid_map[uid]

#    def ping_reegistered_services(self):
#        to_remove = list()
#        for uid, prop in self.uid_map.items():
#            host, port = prop['host_tuple']
#            rs = ServiceModule.remote_service_from_callback_names(cb_names=prop['callbacks'],
#                                                                  host=host,
#                                                                  port=port)
#            if not rs.UNDERTOW_PING():
#                to_remove.append(uid)
#
#        for uid in to_remove:
#            logger.info("Removing [%s]" % uid)
#            self.remove_from_register(uid)
#            self.pretty_print_services()

    @Expose()
    def add_to_register(self, host, port, service_name, callbacks):
        uid = uuid.uuid4()
        logger.info("Registered %s on %s:%d [%s]" % (str(service_name),
                                                          host, port, str(uid)[:8]))
        if service_name not in self.registered_services:
            self.registered_services[service_name] = list()
        self.registered_services[service_name].append(uid)

        self.uid_map[uid] = dict(uid=uid,
                                 host_tuple=(host, port), last_seen=time.time(),
                                 service_name=service_name, callbacks=callbacks)
        self.pretty_print_services()
        return uid

    @Expose()
    def get_hosts_of_service(self, service_name, test_services_first=True):
        logger.info("Got request for service: '%s'" % service_name)
        uids_of_service = self.registered_services.get(service_name, [])
        props = [self.uid_map[uid] for uid in uids_of_service]

        if test_services_first:
            responders = list()
            for prop in props:
                host, port = prop['host_tuple']
                try:
                    #ServiceModule.remote_service(host=host,
                    #                             port=port)
                    RemoteServiceWrapper.remote_service(host=host,
                                                        port=port)
                    responders.append(prop)
                except ConnectionRefusedError as e:
                    msg = "Stale service on %s:%s [%s]" % (host, port, prop['uid'])
                    logger.warning(msg)
                    self.registered_services[service_name].remove(prop['uid'])
        else:
            responders = props

        return responders

