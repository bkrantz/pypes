from compy.metas import force_attr
from compy.metas.actor import ActorMeta

class ScheduledEventProducerMeta(ActorMeta):
    def __new__(cls, name, bases, body):
        force_attr(name=name, body=body, bases=bases, root_class_name="ScheduledEventProducer", attr_name="_parse_interval")
        force_attr(name=name, body=body, bases=bases, root_class_name="ScheduledEventProducer", attr_name="_scheduler_type")
        force_attr(name=name, body=body, bases=bases, root_class_name="ScheduledEventProducer", attr_name="DEFAULT_INTERVAL")
        return ActorMeta.__new__(cls, name, bases, body)