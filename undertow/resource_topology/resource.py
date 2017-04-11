from collections import namedtuple

import attr

@attr.attrs
class Resource(object):
    name = attr.attrib(default=None, init=True)
    path = attr.attrib(default=None, init=True)
    max_instances = attr.attrib(default=None, init=True)
