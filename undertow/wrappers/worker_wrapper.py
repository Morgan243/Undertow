import attr
import time
from undertow import utils

logger = utils.setup_logger(name='service')

@attr.attributes
class WorkerWrapper(object):
    et = attr.attr(default=None, init=False)
    repr = attr.attr(default=None, init=False)
    wrk_target = attr.attr(default=None, init=False)
    wrk_args = attr.attr(default=attr.Factory(list), init=False)
    wrk_kwargs = attr.attr(default=attr.Factory(dict), init=False)
    wrk_thread = attr.attr(default=None, init=False)
    wrk_container_type = attr.attr(default=None, init=False)
    is_running = attr.attr(default=False, init=False)
    launch_time = attr.attr(default=None, init=False)
    stop_time = attr.attr(default=None, init=False)

    def launch(self):

        self.wrk_thread = utils.thread(target=self.wrk_target, name='worker',
                                       args=self.wrk_args, kwargs=self.wrk_kwargs)
        self.launch_time = time.time()
        self.is_running = True
        return self

    def wait_on(self, timeout=None):
        self.wrk_thread.join(timeout=timeout)
        return self

    @staticmethod
    def worker(target, wrk_args=None, wrk_kwargs=None, launch=False, container_type=None):
        if not callable(target):
            raise TypeError("Target in worker is not callable: %s" % str(target))

        wrk = WorkerWrapper()
        wrk.repr = utils.get_repr(target)
        wrk.wrk_target = target
        wrk.wrk_container_type = container_type

        if wrk_args is not None:
            wrk.wrk_args = wrk_args

        if wrk_kwargs is not None:
            wrk.wrk_kwargs = wrk_kwargs

        if launch:
            wrk.launch()
        return wrk

    def __call__(self, *args, **kwargs):
        self.wrk_args += [a for a in args if a not in self.wrk_args]
        self.wrk_kwargs.update(kwargs)
        self.launch()
        return self