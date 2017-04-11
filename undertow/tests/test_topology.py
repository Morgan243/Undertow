from os.path import expanduser, join
import unittest
import getpass

from undertow.resource_topology import Machine, Resource, Topology

l_host = '127.0.0.1'
l_port = 9876
p = '/home/morgan/'

home = expanduser("~")
pkey_path = join(home, '.ssh', 'id_rsa')

class TopologyTests(unittest.TestCase):
    def test_machine_creation(self):
        machine = Machine(hostname='127.0.0.1',
                          username=getpass.getuser(),
                          ssh_user=getpass.getuser(),
                          ssh_port=22,
                          python_bin_path='python')

    def test_create_resource_instance(self):
        resource = Resource(name='mem_key_value',
                            path='/home/morgan/Projects/Undertow.git/undertow/examples/',
                            max_instances=1)

        machine = Machine(hostname='localhost',
                          username=getpass.getuser(),
                          ssh_user=getpass.getuser(),
                          ssh_port=22,
                          python_bin_path='python',
                          pkey_path=pkey_path,
                          local_resources=[resource])

        instance = machine.create_resource_instance(resource_name='mem_key_value')

        self.assertTrue(not instance.is_stopped)
        instance.stop()
        self.assertTrue(instance.is_stopped)

    def test_instance_std_io(self):
        resource = Resource(name='Key Value Store',
                            path='/home/morgan/Projects/Undertow.git/undertow/examples/mem_key_value.py',
                            max_instances=1)

        machine = Machine(hostname='localhost',
                          username=getpass.getuser(),
                          ssh_user=getpass.getuser(),
                          ssh_port=22,
                          python_bin_path='python',
                          pkey_path=pkey_path,
                          local_resources=[resource])

        instance = machine.create_resource_instance(resource_name='Key Value Store')

        #data = instance.ssh_stdout.read()
        #print("Data: " + str(data))
        self.assertTrue(not instance.is_stopped)
        instance.stop()
        self.assertTrue(instance.is_stopped)
