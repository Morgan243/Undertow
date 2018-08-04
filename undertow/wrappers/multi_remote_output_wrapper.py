import attr
from undertow import utils

logger = utils.setup_logger(name='service')

@attr.attributes
class MultiRemoteOutputWrapper(object):
    service_results = attr.attr(default=None)
    res = attr.attr(default=attr.make_class('MultiResult', dict()), init=False)
    values = attr.attr(default=None)

    def multi_remote_outputs(self, service_results, as_sequence=False):
        """service results is a lis of tuples

        s[0] is the service object and s[1] is either
            - (sequence call) a list of dictionaries with keys func, args, kwargs, returned
            - (single call) a list of returned objects
        """
        self.service_results = service_results
        #if isinstance(self.service_results[0], tuple):
        if not as_sequence:
            self.values = [v[1] for v in self.service_results]
        #elif isinstance(self.service_results[0], dict):
        else:
            # through list of tuples
            for sres in self.service_results:
                # Pull out the service results dict
                for sr in sres[1]:
                    res_p = getattr(self, sr['func'], list()) + [sr['returned']]
                    setattr(self, sr['func'], res_p)

            self.values = [sres[1] for sres in self.service_results]
        return self

    def __getitem__(self, item):
        if isinstance(item, int):
            if item >= len(self.service_results):
                raise ValueError("MultiremoteResults got out of bound index: %d" % item)
            return self.values[item]

        else:
            raise NotImplementedError("Only integer indexing works")

