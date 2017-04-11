from undertow.service import Expose
import attr

@Expose()
@attr.attributes
class ScratchPad(object):
    primary_store = attr.attr(default=attr.Factory(dict))

    @Expose()
    def eval(self, expression, globals=None, locals=None):
        return eval(expression, globals, locals)

    @Expose()
    def exec(self, object, globals=None, locals=None):
        return exec(object, globals, locals)

    @Expose()
    def put(self, key, value):
        self.primary_store[key] = value

    @Expose()
    def get(self, key, default=None):
        return self.primary_store.get(key, default)

    @Expose()
    def size(self):
        return len(self.primary_store)

if __name__ == "__main__":
    from undertow.service import ServiceModule
    rs_kv = ServiceModule.discover(ScratchPad)
    rs_kv.exec("print(\'hello world\');")

