import attr
from undertow import utils

@attr.attributes
class RemoteOutputWrapper(object):
    #service_results = attr.attr(default=None)
    #res = attr.attr(default=attr.make_class('MultiResult', dict()), init=False)
    requested_by = attr.attr(default=None)
    produced_by = attr.attr(default=None)
    value = attr.attr(default=None)

    def remote_output(self, service, output):
        #self.service_results = service_results
        self.produced_by = service
        self.value = output
        return self

    def __getitem__(self, item):
        if isinstance(item, int):
            if item >=len(self.service_results):
                raise ValueError("MultiremoteResults got out of bound index: %d" % item)
            return self.values[item]

        else:
            raise NotImplementedError("Only integer indexing works")
