import getpass
from sshtunnel import SSHTunnelForwarder
import paramiko


def tunnel_to(ssh_host, ssh_port, remote_bind_port,
              ssh_pkey=None,
              user=None, password=None,
              allow_prompt=True):
    if not allow_prompt:
        if password is None:
            raise ValueError("No password for ssh tunnel")
        if user is None:
            raise ValueError("No user for ssh tunnel")

    tun_kwargs = dict(ssh_address_or_host=(ssh_host, ssh_port),
                      remote_bind_address=('127.0.0.1', remote_bind_port),
                      ssh_username=user)
    if user is None:
        user = input("Enter ssh user for %s: " % ssh_host)

    if ssh_pkey is not None:
        tun_kwargs['ssh_pkey'] = ssh_pkey
    elif password is None and ssh_pkey is None:
        tun_kwargs['ssh_password'] = getpass.getpass("Enter password %s@%s: " % (user, ssh_host))
    elif password is not None:
        tun_kwargs['ssh_password'] = password

    #ssh.load_system_host_keys()

    print("Creating SSH TunnelForwarder")
    print("\t{user}@{host}:{port}".format(user=user, host=ssh_host,
                                          port=ssh_port))
    server = SSHTunnelForwarder(**tun_kwargs)

    server.start()
    print("Forwarder started")

    #print(server.local_bind_port)  # show assigned local port
    # work with `SECRET SERVICE` through `server.local_bind_port`.

    #server.stop()
    return server

def reverse_tunnel(ssh_host, ssh_port, remote_listen_port, user=None,
                   password=None, allow_prompt=True, pkey=None,
                   handler=None):
    """
    Create a remote forward (reverse tunnel) between calling machine and ssh machin

    """
    if not allow_prompt:
        if password is None:
            raise ValueError("No password for ssh tunnel")
        if user is None:
            raise ValueError("No user for ssh tunnel")

    con_kwargs = dict(hostname=ssh_host, port=ssh_port,
                      #remote_bind_address=('127.0.0.1', remote_listen_port),
                      username=user)


    if user is None:
        user = input("Enter ssh user for %s: " % ssh_host)

    if pkey is not None:
        con_kwargs['pkey'] = pkey
    elif password is None:
        con_kwargs['password'] = getpass.getpass("Enter password %s@%s: " % (user, ssh_host))
    else:
        con_kwargs['password'] = password

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(**con_kwargs)
    except Exception as e:
        print('*** Failed to connect to %s:%d: %r' % (ssh_host, ssh_port, e))

    transport = client.get_transport()
    transport.request_port_forward(address='127.0.0.1',
                                   port=remote_listen_port)
    return client


if __name__ == "__main__":
    tunnel_to('guster', 1337,
              'morgan', '')