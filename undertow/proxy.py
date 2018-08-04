import time
import sys
import argparse
import uuid
import attr
import random
from undertow import utils
from undertow.service import Expose, Worker
from undertow.service import ServiceModule as sm
from undertow.net_core.bsd_socket import NetCore
from undertow.net_core.ssh_tunnel import tunnel_to, reverse_tunnel
from undertow.net_core.net_connection import NetConnection
from undertow.resource_topology.machine import Machine
from undertow import configuration

@Expose('proxy')
@attr.attributes
class Proxy(object):
    service_map = attr.attrib(attr.Factory(dict))
    host_to_proxy_id_map = attr.attrib(attr.Factory(dict))
    machine_proxy_instance_map = attr.attrib(attr.Factory(dict))
    machine_reverse_proxy_instance_map = attr.attrib(attr.Factory(dict))

    flush_thread = attr.attrib(None, init=False)
    done = attr.attrib(False, init=False)
    #@Worker()
    #def flush_worker(self):
    #    i = 0
    #    while True:
    #        print("hello: %d" % i)
    #        time.sleep(2)
    #def flush(self):
    #    while not self.done:
            #for hostname, r_client in self.machine_reverse_proxy_instance_map.items():

    #def launch_flush_thread(self):
    #    utils.thread(target=)

    @Expose()
    def launch_local_service(self, module_path):
        s = sm.launch_from_module_file(module_path=module_path)

        sid = uuid.uuid4()
        self.service_map[sid] = s
        return sid

    @Expose()
    def remote_proxy_to_machine(self, machine):
        if machine.hostname in self.machine_proxy_instance_map:
            raise ValueError("Machine %s already has a proxy")

        print("Proxying to %s" % machine.hostname)
        net_con = NetConnection(host=machine.ssh_host,
                                port=random.randint(1000, 9000))

        net_con.open_tunnel(user=machine.ssh_user, password=None,
                            ssh_port=machine.ssh_port)

        # Get this proxies host and port info
        cb = sm.get_available_callbacks(Proxy, return_all=False)
        if cb is None:
            #rcli = reverse_tunnel(ssh_host=machine.ssh_host, ssh_port=machine.ssh_port,
            #                      remote_listen_port=net_con.port, user=machine.ssh_user)

            local_proxy = sm.launch(Proxy, host='127.0.0.1',
                                    port=net_con.tunnel.local_bind_port)
            #local_proxy = sm.launch(Proxy, socket=rcli.get_transport())
            cb = local_proxy.callbacks
        #host, port = cb.get_host_port()
        rcli = reverse_tunnel(ssh_host=machine.ssh_host, ssh_port=machine.ssh_port,
                              remote_listen_port=port, user=machine.ssh_user)


        # TODO: Shouldn't this be the parent proxy hostname, not local host?
        #parent_proxy_str = "%s:%s"%('127.0.0.1', str(port))
        parent_proxy_str = "%s:%s" % (NetCore.get_net_address(return_one=True), str(port))
        bind_str = "%s:%s" % ('127.0.0.1', net_con.port)
        #parent_proxy_str = "%s:%s"%('127.0.0.1', str(net_con.port))
        prxy_id = str(uuid.uuid4())[:8]
        cmd_str = "-m undertow.proxy --parent-proxy {pp} --bind-addr {ba} --proxy-id {prxy_id}"
        cmd_str = cmd_str.format(pp=parent_proxy_str,
                                 ba=bind_str,
                                 prxy_id=prxy_id)

        print("Sending Command String: %s" % cmd_str)
        mi = machine.create_instance_from_cmd_string(sm.get_undertow_alias(Proxy),
                                                     cmd_str=cmd_str)
        self.machine_proxy_instance_map[machine.hostname] = mi
        self.machine_reverse_proxy_instance_map[machine.hostname] = rcli
        self.host_to_proxy_id_map[machine.hostname] = prxy_id
        return prxy_id

    @Expose()
    def register_proxy_child(self, host, port, prxy_id):
        """Other proxies call this to register themselves for routing later"""
        print("Registering child from %s:%s" % (str(host), str(port)))
        self.service_map[prxy_id] = sm.remote_service(host, port)

    @Expose()
    def proxy_call(self, dest_hostname, service_name,
                   func_str, *args, **kwargs):
        for hostname, machine in self.machine_proxy_instance_map.tems():
            if hostname == dest_hostname:
                rs = self.service_map[self.host_to_proxy_id_map[hostname]]

    @Expose()
    def proxy_through_machines(self, machine_list):
        if not isinstance(machine_list, list):
            machine_list = [machine_list]

        m = machine_list[0]
        # Creates tunnel to the machine and opens a proxy instance on the machine
        prxy_id = self.remote_proxy_to_machine(m)
        while prxy_id not in self.service_map:
            time.sleep(.01)

        if len(machine_list) == 1:
            return

        remaining_machines = machine_list[1:]
        remote_proxy = self.service_map[prxy_id]
        remote_proxy.proxy_through_machines(remaining_machines)
        return

    @staticmethod
    def parse_proxy_path(pp_str, tunnel_sep='->', path_sep=';',
                         default_user=None):
        paths = pp_str.split(path_sep)
        paths = [p.split(tunnel_sep) for p in paths]

        proxy_path_map = dict()
        for p in paths:
            proxy_path = list()
            for host_str in p:
                try:
                    user, host = host_str.split('@')
                except ValueError as e:
                    host = host_str
                    user = default_user

                try:
                    host, port = host.split(':')
                except ValueError as e:
                    host = host
                    port = None

                td = dict(user=user,
                          host=host,
                          port=port)
                proxy_path.append(td)

            proxy_path_map[str(uuid.uuid4())[:8]] = proxy_path

        return proxy_path_map


if __name__ == """__main__""":
    parser = argparse.ArgumentParser()

    parser.add_argument('--start-proxy', dest='start_proxy',
                        action='store_true',
                        default=False)
    parser.add_argument('--bind-addr', dest='proxy_bind_addr',
                        type=str, default=None)
    parser.add_argument('--parent-proxy', dest='parent_proxy_str',
                        type=str, default=None)
    parser.add_argument('--proxy-id', dest='proxy_id',
                        type=str, default=None)

    parser.add_argument('--proxy-user', dest='proxy_user',
                        type=str, default=None)
    parser.add_argument('--proxy-path', dest='proxy_path_str',
                        type=str, default=None)
    parser.add_argument('--list-known-machines', dest='list_machines',
                        action='store_true',
                        default=False)

    args = parser.parse_args()

    if args.list_machines:
        for m in configuration.get_known_machines():
            print("="*30)
            print(m)
        sys.exit(0)

    if args.proxy_bind_addr is not None and args.parent_proxy_str is not None:
        print("Child proxy starting")
        prx_h, prx_p = utils.host_port_from_str(args.proxy_bind_addr)
        this_proxy = sm.launch(Proxy, host=prx_h, port=prx_p)

        host, port = utils.host_port_from_str(args.parent_proxy_str)
        parent_proxy = sm.remote_service(host=host, port=port)
        parent_proxy.register_proxy_child(prx_h, prx_p,
                                          prxy_id=args.proxy_id)
        this_proxy.wait_on()

    if args.proxy_path_str is not None:
        print("PROXY PATH: %s" % args.proxy_path_str)
        proxies = Proxy.parse_proxy_path(pp_str=args.proxy_path_str,
                                         default_user=args.proxy_user)
        path_map_by_machine = dict()
        for pxy_id, proxy_path in proxies.items():
            machine_list = list()
            for p in proxy_path:
                machines = [m for m in configuration.get_known_machines()
                            if m.hostname == p['host']]
                machine_list.append(machines[0])

            path_map_by_machine[pxy_id] = machine_list

        offline_prx = Proxy()
        for pxy_id, machine_list in path_map_by_machine.items():
            offline_prx.proxy_through_machines(machine_list)





