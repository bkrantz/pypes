
from compy.metas import force_attr

class BaseMatchedEventBoxMeta(type):
    def __new__(cls, name, bases, body):
        force_attr(name=name, body=body, bases=bases, root_class_name="BaseMatchedEventBox", attr_name="joined")
        return type.__new__(cls, name, bases, body)
