import os
import paramiko
import attr
import uuid
from undertow.utils import setup_logger, thread

logger = setup_logger(name='Machine Resource')

@attr.attributes
class MachineInstance(object):
    name = attr.attrib(default=None, init=True)
    ssh_client = attr.attrib(default=None, init=True)
    cmd_str = attr.attrib(default=None, init=True)

    ssh_stdin = attr.attrib(default=None, init=False)
    ssh_stdout = attr.attrib(default=None, init=False)
    ssh_stderr = attr.attrib(default=None, init=False)

    stdout_data = attr.attrib(default=None, init=False)
    stderr_data = attr.attrib(default=None, init=False)

    exec_thread = attr.attrib(default=None, init=False)
    is_stopped = attr.attrib(default=False, init=False)
    uid = attr.attrib(attr.Factory(uuid.uuid4))

    def stop(self):
        #self.ssh_stdin.flush()
        #self.ssh_stdout.flush()
        #self.ssh_stderr.flush()
        self.ssh_client.close()
        self.exec_thread.join()
        self.is_stopped = True

    def exec(self):
        try:
            io = self.ssh_client.exec_command(self.cmd_str,
                                              get_pty=True)
            self.ssh_stdin, self.ssh_stdout, self.ssh_stderr = io
        except EOFError as e:
            pass

    def start(self):
        self.exec_thread = thread(target=self.exec)
        return self

    def read_stdout(self):
        ret = self.stdout_data
        #self.stdout_data =

@attr.attributes
class Machine(object):
    # Ssh details
    hostname = attr.attrib(default=None, init=True)
    username = attr.attrib(default=None, init=True)

    ssh_user = attr.attrib(default=None, init=True)
    ssh_host = attr.attrib(default=None, init=True)
    ssh_port = attr.attrib(default=None, init=True)

    # Python path to use when launching on this machine
    python_bin_path = attr.attrib(default=None, init=True)
    # Resource objects representing machine capabilities (services)
    local_resources = attr.attrib(default=None, init=True)
    tunnel_to = attr.attrib(default=True, init=True)
    pkey_path = attr.attrib(default=None, init=True)
    # MachineInfo objects representing machine's reachable from this
    neighbors = attr.attrib(default=None, init=True)

    uid = attr.attrib(attr.Factory(uuid.uuid4))

    def get_resource(self, resource_name):
        resource_matches = [r for r in self.local_resources
                            if r.name == resource_name]

        if len(resource_matches) > 1:
            msg = "Machine %s had %d resources with name %s"
            raise ValueError(msg % (self.hostname,
                                   len(resource_matches),
                                   resource_name))
        elif len(resource_matches) == 0:
            msg = "Machine %s had no resources with name %s"
            raise ValueError(msg % (self.hostname, resource_name))

        resource = resource_matches[0]
        return resource

    def create_resource_instance(self, resource_name,
                                 cmd_str=None,
                                 broadcast_for_registry=False,
                                 num_instances=1):
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.hostname, username=self.username)
        resource = self.get_resource(resource_name)
        split_path = os.path.split(resource.path)
        base_dir = split_path[0]
        module = split_path[-1]

        flags = ['' if not broadcast_for_registry else '-d']
        flag_str = " ".join(flags)

        if cmd_str is None:
            cmd = "pushd .;"
            cmd += "cd {dir};"
            cmd += "{bin} -m undertow.service {module} -N {instances} {flags};"
            cmd += "popd"

            cmd = cmd.format(dir=base_dir, bin=self.python_bin_path,
                             module=module,
                             instances=num_instances,
                             flags=flag_str)
        else:
            cmd = cmd_str

        logger.info("Launching with: %s" % cmd)
        mi = MachineInstance(name=resource_name,
                             ssh_client=ssh,
                             cmd_str=cmd)
        mi.start()
        # For newer systems, need pty in order to get cleanup after sudden disconnect
        #ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd, get_pty=True)
        #mi = MachineInstance(name=resource_name,
        #                     ssh_client=ssh,
        #                     ssh_stdin=ssh_stdin,
        #                     ssh_stdout=ssh_stdout,
        #                     ssh_stderr=ssh_stderr)

        return mi

    def create_instance_from_cmd_string(self, instance_name,
                                        cmd_str=None,
                                        broadcast_for_registry=False,
                                        num_instances=1):
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.connect(self.hostname, username=self.username)

        cmd_str = self.python_bin_path + ' ' + cmd_str
        logger.info("Launching: %s" % cmd_str)

        # For newer systems, need pty in order to get cleanup after sudden disconnect
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd_str,
                                                             get_pty=True)
        mi = MachineInstance(name=instance_name,
                             ssh_client=ssh, cmd_str=cmd_str)
        return mi


