from undertow.service import Expose, Worker
import time
import os

@Expose()
class Basic(object):
    @Expose()
    def get_cwd(self):
        return str(os.getcwd())

    @Expose(container_type='process')
    def get_env(self):

        return dict(os.environ)

    @Worker()
    def monitor(self):
        print("Worker going")
        while True:
            time.sleep(.5)


if __name__ == "__main__":
    from undertow.service import ServiceModule
    rs_basic = ServiceModule.discover(Basic)
    print(rs_basic.get_cwd())
    print(rs_basic.get_env())

