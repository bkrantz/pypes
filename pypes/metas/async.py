from pypes.metas import force_root_attr, force_root_ignore, force_derivative_attr, force_derivative_ignore, force_root_only
from pypes import import_restriction

__all__ = []

if __name__.startswith(import_restriction):
	__all__ += [
		"AsyncMeta"
	]

class IgnoreDerivativesMeta(type):
	def __new__(cls, name, bases, body):
		force_root_only(name=name, root_class_name=cls._root_class_name)
		return type.__new__(cls, name, bases, body)

class KilledExceptionMeta(IgnoreDerivativesMeta):
	_root_class_name = "KilledException"

class AsyncManagerMeta(IgnoreDerivativesMeta):
	_root_class_name = "AsyncManager"

class RestartPoolMeta(IgnoreDerivativesMeta):
	_root_class_name = "RestartPool"

class RestartableGreenletMeta(IgnoreDerivativesMeta):
	_root_class_name = "RestartableGreenlet"


class AsyncContextManagerMeta(type):
	_root_class_name = "AsyncContextManager"

	def __new__(cls, name, bases, body):
		ignore_derivative_attrs = ["__enter__", "__exit__",
		"_AsyncContextManager__respawn_stopped_greenlets",
		"_AsyncContextManager__kill_running_greenlets",
		"_AsyncContextManager__force_running",
		"_swap_greenlets", "_pop_greenlet", "spawn_greenlet",
		"running", "wait_for_running", "wait_for_stopping", "trigger_stop"]

		#force_derivative_attrs = ["start", "stop"]

		for attr in ignore_derivative_attrs:
			force_derivative_ignore(name=name, body=body, bases=bases, root_class_name=AsyncContextManagerMeta._root_class_name
, attr_name=attr)
			force_root_attr(name=name, body=body, bases=bases, root_class_name=AsyncContextManagerMeta._root_class_name
, attr_name=attr)
		'''for attr in force_derivative_attrs:
			force_derivative_attr(name=name, body=body, bases=bases, root_class_name=AsyncContextManagerMeta._root_class_name
, attr_name=attr)
			force_root_ignore(name=name, body=body, bases=bases, root_class_name=AsyncContextManagerMeta._root_class_name
, attr_name=attr)
		'''
		return type.__new__(cls, name, bases, body)