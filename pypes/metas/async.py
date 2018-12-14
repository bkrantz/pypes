from pypes.metas import force_class_attr, force_class_ignore, force_derivative_attr, force_derivative_ignore
from pypes import import_restriction

__all__ = []

if __name__.startswith(import_restriction):
	__all__ += [
		"AsyncMeta"
	]

class AsyncMeta(type):
	def __new__(cls, name, bases, body, root_name=""):
		ignore_derivative_attrs = ["__enter__", "__exit__", "start", "stop", "spawn_thread", "block", "is_running", "sleep", "wait"]

		for attr in ignore_derivative_attrs:
			force_derivative_ignore(name=name, body=body, bases=bases, root_class_name=root_name, attr_name=attr)

		return type.__new__(cls, name, bases, body)