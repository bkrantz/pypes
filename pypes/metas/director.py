from pypes.metas import force_attr_instance, force_attr_subclass, force_class_attr, force_class_ignore, force_derivative_attr, force_derivative_ignore
from pypes import import_restriction
from pypes.metas.async import AsyncMeta
from pypes.event import BaseEvent
import types
__all__ = []

if __name__.startswith(import_restriction):
	__all__ += [
		"ActorMeta"
	]

class ActorMeta(AsyncMeta):
	def __new__(cls, name, bases, body):
		root_name = "Actor"
		force_derivative_funcs = ["consume"]
		ignore_derivative_funcs = ["_Actor__connect_queue", "_Actor__register_consumer", "_Actor__loop_send", 
		"_Actor__generate_split_id", "_Actor__consumer", "_Actor__try_spawn_consume", "_Actor__consume_pre_processing",
		"_Actor__consume_post_processing", "_Actor__consume_wrapper", "_Actor__do_consume", "_Actor__send_event", "_Actor__send_error",
		"_Actor__format_event", "_Actor__format_queues", "create_event", "connect_error_queue", "connect_log_queue", "connect_queue"]

		#force derivative implementations
		for attr in force_derivative_funcs:
			force_derivative_attr(name=name, body=body, bases=bases, root_class_name=root_name, attr_name=attr)
			force_class_ignore(name=name, body=body, bases=bases, root_class_name=root_name, attr_name=attr)
			force_attr_instance(body=body, attr_name=attr, clazz=types.FunctionType, name=name)

		#ignore derivative implementations
		for attr in ignore_derivative_funcs:
			force_class_attr(name=name, body=body, bases=bases, root_class_name=root_name, attr_name=attr)
			force_derivative_ignore(name=name, body=body, bases=bases, root_class_name=root_name, attr_name=attr)
			force_attr_instance(body=body, attr_name=attr, clazz=types.FunctionType, name=name)

		#force types
		force_attr_subclass(body=body, attr_name="input", clazz=BaseEvent, name=name)
		force_attr_subclass(body=body, attr_name="output", clazz=BaseEvent, name=name)

		return AsyncMeta.__new__(cls, name, bases, body, root_name=root_name)