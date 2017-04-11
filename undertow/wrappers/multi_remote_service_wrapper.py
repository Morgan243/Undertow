import attr
import uuid
import queue
import time
from undertow.net_core.bsd_socket import NetCore
from undertow import utils
from undertow.wrappers.multi_remote_output_wrapper import MultiRemoteOutputWrapper
from undertow.wrappers.remote_service_wrapper import RemoteServiceWrapper

logger = utils.setup_logger(name='service')
default_port = 2438

@attr.attributes
class MultiRemoteServiceWrapper(object):
    remote_services = attr.attr(default=None)
    serial = attr.attr(default=attr.make_class('MultiMethod', dict()), init=False)
    parallel = attr.attr(default=attr.make_class('ParallelMultiMethod', dict()), init=False)
    results = attr.attr(default=attr.Factory(queue.Queue))
    delay_between_work = attr.attr(default=None)

    call_queue = attr.attr(default=attr.Factory(queue.Queue))

    @staticmethod
    def check_for_matching_services(remote_s):
        for s in remote_s:
            if s.name != remote_s[0].name:
                print("%s not equal to %s" %(s.name, remote_s[0].name))
                return False

        return True

    @staticmethod
    def create_multi_partial(f_name, services, threads=None):
        def multi_run(*args, **kwargs):
            res = list()
            for s in services:
                obj = s.exec_remote_callback(cb_func=f_name, cb_args=args,
                                             cb_kwargs=kwargs)
                res.append((s, obj))

            return MultiRemoteOutputWrapper().multi_remote_outputs(res)
        return multi_run

    def exec_and_store_result(self, f_name, args, kwargs, service):
        obj = service.exec_remote_callback(cb_func=f_name, cb_args=args,
                                           cb_kwargs=kwargs)
        self.results.put((service, obj))

    def create_parallel_multi_partial(self, f_name, services):
        def parallel_multi_run(*args, **kwargs):
            threads = list()
            for s in services:
                th = utils.thread(target=self.exec_and_store_result,
                                  kwargs=dict(f_name=f_name, args=args, kwargs=kwargs,
                                              service=s))
                threads.append(th)

            [th.join() for th in threads]
            res = list()
            while self.results.qsize() != 0:
                res.append(self.results.get())

            return MultiRemoteOutputWrapper().multi_remote_outputs(res)
        return parallel_multi_run

    def work_on_call_queue(self, service):
        while True:
            try:
                idx, f, args, kwargs = self.call_queue.get(block=False, timeout=1)

                obj = service.exec_remote_callback(cb_func=f,
                                                   cb_args=args, cb_kwargs=kwargs)
                #obj = NetCore.exec_remote_callback(host=service.host,
                #                                   port=service.port, cb_func=f,
                #                                   cb_args=args, cb_kwargs=kwargs)
                self.results.put((idx, service, obj))
                #if self.delay_between_work is not None:
                #    time.sleep(self.delay_between_work)

            except queue.Empty as e:
                print("No more work")
                break
        print("work on call queue ending")

    def work_on_sequence_call_queue(self, service):
        while True:
            try:
                idx, seq = self.call_queue.get(block=False, timeout=1)
                seq_res = list()
                #seq_res = dict()
                for f, args, kwargs in seq:
                    obj = service.exec_remote_callback(cb_func=f,
                                                       cb_args=args, cb_kwargs=kwargs)
                    #obj = NetCore.exec_remote_callback(host=service.host,
                    #                                   port=service.port, cb_func=f,
                    #                                   cb_args=args, cb_kwargs=kwargs)
                    seq_res.append(dict(func=f, args=args, kwargs=kwargs,
                                        returned=obj))

                self.results.put((idx, service, seq_res))

            except queue.Empty as e:
                print("No more work")
                break
        print("work on call queue ending")


    def map_sequence(self, f_seq, *sequence_args):
        if len(f_seq) != len(sequence_args):
            raise ValueError("f_seq not equal in length to sequence_args")
        for sa in sequence_args:
            if sa is not None and not isinstance(sa, list) and not isinstance(sa, dict):
                raise ValueError("Each sequence arg must be None or a dict")

        sizes = list({len(sa) for sa in sequence_args if sa is not None and not isinstance(sa, dict)})
        if len(sizes) > 1:
            raise ValueError("Non-None sequence args must be the same length")

        if len(sizes) == 0:
            raise ValueError("Nothing to iterate in provided sequence args")

        num_tasks = sizes[0]

        for idx in range(0, num_tasks):
            #       func, *args,
            seq = [(f, list(), sequence_args[fi][idx]
                    if sequence_args[fi] is not None and not isinstance(sequence_args[fi], dict)
                    else
                    dict() if sequence_args[fi] is None else sequence_args[fi])
                            for fi, f in enumerate(f_seq)]
            self.call_queue.put((idx, seq))

        workers = list()
        for s in self.remote_services:
            th = utils.thread(target=self.work_on_sequence_call_queue,
                              kwargs=dict(service=s))
            workers.append(th)

        from tqdm import tqdm
        with tqdm(total=num_tasks, desc="Map Sequence on %s" % "->".join(str(fs) for fs in f_seq)) as pbar:
            last = 0
            while self.results.qsize() < num_tasks:
                qs = self.results.qsize()
                if last != qs:
                    pbar.update(qs - last)
                    last = qs
                else:
                    time.sleep(1.25)

            pbar.update(self.results.qsize() - last)

        [w.join() for w in workers]
        res = [None] * self.results.qsize()

        while self.results.qsize() != 0:
            idx, s, seq_r = self.results.get()
            res[idx] = (s, seq_r)
            #res[idx] = self.results.get()
        return MultiRemoteOutputWrapper().multi_remote_outputs(res, as_sequence=True)


    def map(self, f, *args, iterable_args=None, iterable_kwargs=None, **kwargs):
        """"
        Iterable *args/**kwargs are for distinct kwargs
        """
        if iterable_args is None and iterable_kwargs is None:
            raise ValueError("Need at least one of iterable args or iterable kwargs")

        if iterable_args is None:
            iterable_args = [() for i in range(0, len(iterable_kwargs))]
        if iterable_kwargs is None:
            iterable_kwargs = [dict() for i in range(0, len(iterable_args))]

        iter_map_args = list(zip(iterable_args, iterable_kwargs))
        num_tasks = len(iter_map_args)
        for idx, (it_args, it_kwargs) in enumerate(iter_map_args):

            kw = dict(kwargs)
            kw.update(it_kwargs)
            self.call_queue.put((idx, f, list(args) + list(it_args), kw))

        #print("Call queue size : %d" % self.call_queue.qsize())

        workers = list()
        for s in self.remote_services:
            th = utils.thread(target=self.work_on_call_queue,
                              kwargs=dict(service=s))
            workers.append(th)

        from tqdm import tqdm
        with tqdm(total=num_tasks, desc="Map on %s" % str(f)) as pbar:
            last = 0
            while self.results.qsize() < num_tasks:
                qs = self.results.qsize()
                if last != qs:
                    pbar.update(qs - last)
                    last = qs
                else:
                    time.sleep(1.25)

            pbar.update(self.results.qsize() - last)

        [w.join() for w in workers]
        res = [None] * self.results.qsize()

        while self.results.qsize() != 0:
            idx, s, r = self.results.get()
            res[idx] = (s, r)
        return MultiRemoteOutputWrapper().multi_remote_outputs(res)

    def multi_remote_service(self, services):
        self.remote_services = services
        if not MultiRemoteServiceWrapper.check_for_matching_services(services):
            raise NotImplementedError("Can't handle multi remote of varied service type")

        self.callbacks = services[0].fetch_callbacks().callback_map

        for f_name in self.callbacks:
            if f_name not in dir(self):
                setattr(self, f_name, MultiRemoteServiceWrapper.create_multi_partial(f_name, services))

            setattr(self.serial, f_name, MultiRemoteServiceWrapper.create_multi_partial(f_name, services))
            setattr(self.parallel, f_name, self.create_parallel_multi_partial(f_name, services))

        return self
