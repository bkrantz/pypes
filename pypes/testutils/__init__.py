import unittest
from pypes.globals.async import get_restart_pool, get_async_manager
from pypes.util.async import sleep
from pypes.util import RedirectStdStreams

class BaseUnitTest(unittest.TestCase):

	def setUp(self):
		with RedirectStdStreams():
			get_async_manager()._AsyncManager__managers = {}
			get_restart_pool().kill()
			sleep(); sleep(); sleep()

	def tearDown(self):
		with RedirectStdStreams():
			get_async_manager()._AsyncManager__managers = {}
			get_restart_pool().kill()
			sleep(); sleep(); sleep()

def funcs_tester(clazz, func_definitions={}, *args, **kwargs):
	class MixinClass:
			@staticmethod
			def get_names(func_name):
				return "did_%s" % func_name, "args_%s" % func_name, "kwargs_%s" % func_name, "count_%s" % func_name
			@staticmethod
			def get_class_name(func_name):
				return "%s_mixin_class"
			@staticmethod
			def get_placeholder_func_name(func_name):
				return "%s_placeholder" % func_name
			def mixin_func(self, mixin_func_name=None, mixin_returns=None, *args, **kwargs):
				did_attr_name, args_attr_name, kwargs_attr_name, count_attr_name = MixinClass.get_names(func_name=mixin_func_name)
				setattr(self, did_attr_name, True)
				setattr(self, args_attr_name, args)
				setattr(self, kwargs_attr_name, kwargs)
				setattr(self, count_attr_name, getattr(self, count_attr_name, 0)+1)
				return mixin_returns

	def get_mixin(current_mixin_func_name, returns):
		func_did, func_args, func_kwargs, func_count = MixinClass.get_names(func_name=current_mixin_func_name)
		return type(
			MixinClass.get_class_name(func_name=current_mixin_func_name), 
			(MixinClass, object,), 
			{
				MixinClass.get_placeholder_func_name(func_name=current_mixin_func_name): (lambda self, *args, **kwargs: self.mixin_func(mixin_func_name=current_mixin_func_name, mixin_returns=returns, *args, **kwargs)),
				func_did: False,
				func_args: None,
				func_kwargs: None,
				func_count: 0
			})
	mixins = tuple([get_mixin(current_mixin_func_name=key, returns=value) for key, value in func_definitions.iteritems()]) + (clazz,)
	new_class = type('DerivativeClass', mixins, {"__init__":clazz.__init__})
	for func_name in func_definitions.iterkeys():
		setattr(new_class, func_name, getattr(new_class, MixinClass.get_placeholder_func_name(func_name=func_name)))
	return new_class

def _test_func(self, obj, func_name, did, args, kwargs, count=0):
	self.assertEqual(getattr(obj, "did_%s" % func_name, None), did)
	self.assertEqual(getattr(obj, "args_%s" % func_name, None), args)
	self.assertEqual(getattr(obj, "kwargs_%s" % func_name, None), kwargs)
	self.assertEqual(getattr(obj, "count_%s" % func_name, None), count)