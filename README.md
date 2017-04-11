## Goal
Provide a flexible framework for ad-hoc computation spanning multiple machines, with focus on interactive and interative use-cases.

## Overview
**Undertow is in a very alpha/beta stage, use at your own risk**

Most easily described as an RPC framework, Undertow aims to bridge the gap between highly structured distributed compute models
(e.g, Spark, Tez, MapReduce), granular message passing (MPI), and the often ad-hoc compute needs of an interactive
research & analysis environment (Jupyter). Focus is on providing a cluster library that
is flexible, easy and quick to setup, secure, and highly pythonic. Undertow is exposes low-level RPC interfaces along with more
abstract simplified interfaces for common use cases. Other compute models, such a graph-based one, could be implemented atop of Undertow.

Currently not compatible with other RPC frameworks, though it may be a priority in
the future.

## Services
Undertow is a library to define and manage computation. A `service` defines
a set of callback methods and worker methods. Callback methods are exposed
to connecting clients and can accept any serializable python arguments.
  
### Compute Methods (RPC)
TODO

### Workers Methods
TODO

## Examples
Below, we create a simple in-memory key-value store. We first `Expose` our
class `MemKeyValue` using the decorator returned by `Expose()`. Note the use
of the attrs library is optional when using Undertow. After exposing the class,
we must then expose the methods of that class that we would like to make available
as an RPC end-point.

```python
from undertow.service import Expose, ServiceModule
import time
import attr

@Expose()
@attr.attributes
class MemKeyValue(object):
    primary_store = attr.attr(default=attr.Factory(dict))

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
    rs_kv = ServiceModule.discover(MemKeyValue)

    n = 10000
    for i in range(0, n):
        rs_kv.put(key=i, value=i*i)

```

Assuming the above is saved as `memkv.py`, the service can be launched by 
using the undertow module directly:
```bash
python -m undertow.service memkv.py
```

Undertow imports the service through the module `memkv.py`, and will 
therefore not pass the 'main condition'. In other words, the above launching
 of the MemKeyValue service (inside the memkv.py file) will not execute 
 as main. Therefore, the example uses this flexibility to invoke a 
 client to the interface defined in the lines above. This is a 
 convenient place to invoke examples, diagnostics, or a user interface. 
Therefore, to run a single client, simply execute the module:
```
python memkv.py
```

The service persists between clients, so later clients will see these values.

## More examples to come
But first, more work
