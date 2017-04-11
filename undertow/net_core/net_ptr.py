#from undertow.net_core.bsd_socket import NetCore
import os
import sys
import time
import threading
import uuid
import attr

from undertow.net_core.serializer import serialize, deserialize

@attr.attributes
class NetPtr(object):
    #callback_request_dict = attr.attr(default=None, init=True)

    callback_func = attr.attr(default=None, init=True)
    callback_args = attr.attr(default=attr.Factory(list))
    callback_kwargs = attr.attr(default=attr.Factory(dict))
    callback_res = attr.attr(default=None, init=True)
    return_output = attr.attr(default=True, init=True)

    container_type = attr.attr(default='thread', init=True)

    compute_sem = attr.attr(attr.Factory(lambda : threading.Semaphore(value=0)))

    uid = attr.attr(default=attr.Factory(uuid.uuid4), init=False)
    create_time = attr.attr(default=attr.Factory(time.time), init=False)
    start_time = attr.attr(default=None, init=False)

    def set_obj(self, obj):
        self.compute_end_t = time.time()
        self.obj = obj
        self.compute_sem.release()

    def is_available(self):
        if self.compute_end_t is not None:
            return True
        else:
            return False

    def run_callback_request(self):
        self.start_time = time.time()

               #print("CONTAINER: %s" % str(container_type))
        # TODOL Clean this up with container abstraction?
        if self.container_type == 'thread':
            ret = self.callback_func(*self.callback_args,
                                     **self.callback_kwargs)
            #ret = cb(*crd['args'],
            #         ** crd['kwargs'])
        elif self.container_type == 'process':
            r, w = os.pipe()
            pid = os.fork()

           # parent
            if pid != 0:
                print("LAUNCHED PROCESS: %d" % pid)
                os.close(w)
                r = os.fdopen(r, 'rb')
                _status = os.waitpid(pid, 0)
                ret_ser = r.read()
                ret = deserialize(ret_ser)
                if isinstance(ret, Exception):
                    raise ret
            else:
                os.close(r)
                w = os.fdopen(w, 'wb')
                try:
                    ret = self.callback_func(*self.callback_args,
                                             **self.callback_kwargs)
                except Exception as e:
                    ret = e

                w.write(serialize(ret))
                w.flush()
                w.close()
                os._exit(0)

        return self.set_obj(ret)


        #self.set_obj(self.callback_func(*self.callback_args,
        #                                **self.callback_kwargs))



        #if callbacks is None:
        #    callbacks = self.cb_container.callback_map

        #crd = self.callback_request_dict
        #try:
        #    if callable(crd['call_name']):
        #        cb = crd['call_name']
                #in_subproc = in_subproc if in_subproc is not None else False
        #    else:
        #        call_name = crd['call_name']
        #        cb = callbacks[call_name]
        #        if container_type is None:
        #            container_type = self.cb_container.callback_container_map[call_name]
                #in_subproc = (in_subproc or
                #              (self.cb_container.callback_container_map[] is not None
                #               and crd['call_name'] in self.in_subproc_callbacks))
        #except KeyError as e:
        #    print("ERROR: no call to '%s' exists " % crd['call_name'])
        #    raise e



    def request(self, block=True):
        # wow, such hack
        from undertow.net_core.bsd_socket import NetCore
        self.block = block
        # This goina break yo
        sock = NetCore.build_client_socket(self.host, self.port)
        response = NetCore.send_then_receive_response(sock, self)

        self.compute_end_t = response.compute_end_t
        self.obj = response.obj
        return self

    def wait_on(self):
        self.compute_sem.acquire(blocking=True)
        return self

    def get(self, block=True):
        self.block = block

        if block:
            return self.wait_on().obj
        else:
            return self.obj

    def __str__(self):
        s = ("NET PTR - %s:%d, obj_id=%s, avail=%s" %
            (self.host, self.port, self.obj_id, self.is_available()))
        return s

