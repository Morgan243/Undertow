from undertow.net_core.ssh_tunnel import tunnel_to
import argparse

if __name__ == """__main__""":
    parser = argparse.ArgumentParser()

    parser.add_argument('--user', dest='ssh_user',
                        type=str, default=None)
    parser.add_argument('--host', dest='ssh_host',
                        type=str, default=None)
    parser.add_argument('--port', dest='ssh_port',
                        type=int, default=22)

    parser.add_argument('--remote-port', dest='remote_port',
                        type=int, default=1337)

    #parser.add_argument('--proxy-user', dest='proxy_user',
    #                    type=str, default=None)
    #parser.add_argument('--proxy-path', dest='proxy_path_str',
    #                    type=str, default=None)
    #parser.add_argument('--list-known-machines', dest='list_machines',
    #                    action='store_true',
    #                    default=False)

    args = parser.parse_args()

    tunnel = tunnel_to(ssh_host=args.ssh_host, ssh_port=args.ssh_port,
                       user=args.ssh_user, remote_bind_port=args.remote_port)

    print(tunnel)
