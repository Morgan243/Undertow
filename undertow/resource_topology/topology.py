from tqdm import tqdm
#from undertow.resource_topology.resource import launch_resource_on_machine
from undertow.resource_topology.machine import Machine, MachineInstance
import attr


@attr.attrs
class Topology(object):
    machine_map = attr.attrib(default=attr.Factory(dict), init=False)
    machine_instances = attr.attrib(default=attr.Factory(dict), init=False)
    list_of_machine_instances = attr.attrib(default=attr.Factory(list), init=False)

    def add_machine(self, machine):
        if machine.hostname not in self.machine_map.keys():
            self.machine_map[machine.hostname] = machine
        else:
            raise ValueError("Attempting to re add this machine: %s" % str(machine))

        return self

    def launch(self, resource_name):
        for mname, m in tqdm(self.machine_map.items(), desc='launching %s' % resource_name):
            for r in m.local_ut_resources:
                if resource_name != r.name:
                    continue

                if mname not in self.machine_instances:
                    self.machine_instances[mname] = dict()
                if resource_name not in self.machine_instances[mname]:
                    self.machine_instances[mname][resource_name] = list()

                mi = m.create_resource_instance(resource_name,
                                                broadcast_for_registry=False, num_instances=1)

                self.list_of_machine_instances.append(mi)
                self.machine_instances[mname][resource_name].append(mi)

    def view(self, idx=0):
        machine = self.list_of_machine_instances[idx]
        while True:
            line = machine.ssh_stdout.readline()
            if not line:
                #yield from asyncio.sleep(.01)
                continue
            #process_line(line)
            if machine.ssh_stdout is None:
                machine.ssh_stdout = ''
            machine.stdout_data += line
            print(machine.stdout_data)

    def stop(self, resource_name=None):
        for mi in self.list_of_machine_instances:
            mi.ssh.close()

if __name__ == """__main__""":
    from undertow import configuration
    t = Topology()
    t.add_machine(configuration.guster)
    t.add_machine(configuration.spencer)

    t.view()
    input("wait")
    t.stop()
