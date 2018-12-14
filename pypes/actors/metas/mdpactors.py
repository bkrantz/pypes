from compy.metas import force_attr
from compy.metas.actor import ActorMeta

class MDPActorMeta(ActorMeta):
    def __new__(cls, name, bases, body):
        force_attr(name=name, body=body, bases=bases, root_class_name="MDPActor", attr_name="send_outbound_message")
        force_attr(name=name, body=body, bases=bases, root_class_name="MDPActor", attr_name="process_inbound_message")
        force_attr(name=name, body=body, bases=bases, root_class_name="MDPActor", attr_name="verify_brokers")
        force_attr(name=name, body=body, bases=bases, root_class_name="MDPActor", attr_name="send_heartbeats")
        return ActorMeta.__new__(cls, name, bases, body)