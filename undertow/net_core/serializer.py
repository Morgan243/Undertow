import pickle


def serialize_pickle(obj):
    return pickle.dumps(obj)


def deserialize_pickle(s):
    return pickle.loads(s)


serialize = serialize_pickle
deserialize = deserialize_pickle
