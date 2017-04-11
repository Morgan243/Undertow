from undertow.service import Expose
import time
import attr

@Expose()
@attr.attributes
class MemKeyValue(object):
    primary_store = attr.attr(default=attr.Factory(dict))

    @Expose()
    def null(self, *args, **kwargs):
        return

    @Expose()
    def put(self, key, value):
        self.primary_store[key] = value

    @Expose()
    def get(self, key, default=None):
        return self.primary_store.get(key, default)

    @Expose()
    def size(self):
        return len(self.primary_store)

    @Expose()
    def clear(self):
        self.primary_store = dict()

if __name__ == "__main__":
    from undertow.service import ServiceModule
    rs_kv = ServiceModule.discover(MemKeyValue)

    n = 10000
    st = time.time()
    for i in range(0, n):
        rs_kv.put(key=i, value=i*i)
        #print(rs_kv.get(i))
        #rs_kv.null(key=i, value='hello')

    delta = time.time() - st
    print("Took %.3fs" % delta)
    print("     ->%.5f" % (delta/float(n)))

