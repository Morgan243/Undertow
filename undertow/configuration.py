from undertow.resource_topology.machine import Machine
from undertow.resource_topology.resource import Resource

#linode = Machine(hostname='linode', python_bin_path='/home/morgan/jupyter/venv/bin/python',
#                 username='morgan', ssh_host='guster', ssh_user='morgan', ssh_port=22,
#                 local_resources=[
#                     Resource(name='text_classification',
#                                path='/home/morgan/Projects/Mill/mill/models/text_classification.py',
#                                max_instances=2)],
#                 tunnel_to=False, neighbors=['spencer', 'starbuck'])

guster = Machine(hostname='guster', python_bin_path='/home/morgan/jupyter/venv/bin/python',
                 username='morgan', ssh_host='guster', ssh_user='morgan', ssh_port=22,
                 local_resources=[
                     Resource(name='text_classification',
                                path='/home/morgan/Projects/Mill/mill/models/text_classification.py',
                                max_instances=2)],
                 tunnel_to=False, neighbors=['spencer', 'starbuck'])
spencer = Machine(hostname='spencer', python_bin_path='/home/morgan/jupyter/venv/bin/python',
                  username='morgan', ssh_host='guster', ssh_user='morgan', ssh_port=22,
                  local_resources=[
                      Resource(name='text_classification',
                                 path='/home/morgan/Projects/Mill/mill/models/text_classification.py',
                                 max_instances=2)],
                  tunnel_to=False, neighbors=['guster', 'starbuck'])
starbuck = Machine(hostname='starbuck', python_bin_path='/home/morgan/venv/bin/python',
                   username='morgan', ssh_host='guster', ssh_user='morgan', ssh_port=22,
                   local_resources=[
                       Resource(name='text_classification',
                                  path='/home/morgan/Projects/Mill/mill/models/text_classification.py',
                                  max_instances=1)],
                   tunnel_to=False, neighbors=['guster', 'spencer'])
def get_known_machines():
    return [guster, spencer, starbuck]

#machine_topologies_desc = dict(
#    home=Topology().add_machine(guster).add_machine(spencer).add_machine(starbuck)
#)

## Defaults
default_port = 2438

default_container_type = 'process'
default_net_core_type = 'bsd'

default_tunnel = 'ssh'
default_ssh_user = ''
default_ssh_auth = 'password'
default_ssh_password = ''


#current_topology = resource_topology.machine_topologies_desc['home']
current_topology = None

# Options
tunnel = False
#tunnel=True
tunnel_for_local_connections = False
#redirect_to_local_host = True
redirect_to_local_host = False
