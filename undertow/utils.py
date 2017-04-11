import threading
import logging

default_format = '[%(asctime)s - %(name)-8s - %(levelname)-4s] %(message)s'
datetime_format = "%Y-%m-%d %H:%M:%S"
default_log_level = logging.DEBUG
handler = logging.StreamHandler()

def setup_logger(logger=None, name=None, log_level=default_log_level,
                 log_format=default_format):
    if logger is None:
        logger = logging.getLogger(name=name)

    formatter = logging.Formatter(log_format, datefmt=datetime_format)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(log_level)
    return logger


def thread(group=None, target=None, name=None,
           args=(), kwargs=None, daemon=True,
           start=True):
    t = threading.Thread(group=group, target=target,
                         name=name, args=args,
                         kwargs=kwargs, daemon=daemon)

    if start:
        t.start()

    return t


def get_repr(obj):
    try:
        repr = str(obj.__name__)
        return repr
    except:
        print("Cant get __class__.__name__ from %s" % obj)

    try:
        repr = type(obj)
        return repr
    except:
        print("Cant get type from %s" % obj)


def load_machine_config_file():
    p = '../machines.cfg'
    print("Path: %s" % p)


    import configparser
    config = configparser.ConfigParser()
    config.read(p)
    print(config.sections())
    machines = dict()
    for s in config.sections():
        machines[s] = {o: config.get(s, o)
                       for o in config.options(s)}

    print(machines)


def module_name_from_file_name(filename):
    if isinstance(filename, list):
        return [module_name_from_file_name(n) for n in filename]
    return filename[:-3] if '.py' == filename[-3:] else filename

def host_port_from_str(hp_str):
    if ':' not in hp_str:
        raise ValueError("Don't understand host+port str: %s" % hp_str)

    host, port = hp_str.split(':')
    return host, int(port)

if __name__ == "__main__":
    load_machine_config_file()
