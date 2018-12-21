from pypes import import_restriction

__all__ = []

if __name__.startswith(import_restriction):
	__all__ += [
		"force_root_only",
		"force_attr_instance",
		"force_attr_subclass",
		"force_class_attr",
		"force_class_ignore",
		"force_derivative_attr",
		"force_derivative_ignore"
	]

def force_root_only(name, root_class_name):
	if name != root_class_name:
		raise TypeError("Class Error: '%s' does not support derivatives.  '%s' is an invalid class definition." % (root_class_name, name))

def force_attr_instance(body, attr_name, clazz, name):
	attr = body.get(attr_name, None)
	if not attr is None and not isinstance(attr, clazz):
		raise TypeError("Attribute Error: '%s' must be a derivative of '%s' for '%s'" % (attr_name, clazz, name))

def force_attr_subclass(body, attr_name, clazz, name):
	attr = body.get(attr_name, None)
	if not attr is None and not issubclass(attr, clazz):
		raise TypeError("Attribute Error: '%s' must be a derivative of '%s' for '%s'" % (attr_name, clazz, name))

def force_root_attr(name, body, bases, root_class_name, attr_name):
	if name == root_class_name:
		if not attr_name in body and not reduce(lambda x,y : x or hasattr(y, attr_name), (False,) + bases[:]):
			raise TypeError("Attribute Error: '%s' not implemented for '%s'" % (attr_name, name))

def force_root_ignore(name, body, bases, root_class_name, attr_name):
	if name == root_class_name:
		if attr_name in body:
			raise TypeError("Attribute Error: Overriding '%s' not allowed in '%s'" % (attr_name, name))
			
def force_derivative_attr(name, body, bases, root_class_name, attr_name):
	if name != root_class_name:
		if not attr_name in body and not reduce(lambda x,y : x or hasattr(y, attr_name), (False,) + bases[:]):
			raise TypeError("Attribute Error: '%s' not implemented for '%s'" % (attr_name, name))

def force_derivative_ignore(name, body, bases, root_class_name, attr_name):
	if name != root_class_name:
		if attr_name in body:
			raise TypeError("Attribute Error: Overriding '%s' not allowed in '%s'" % (attr_name, name))