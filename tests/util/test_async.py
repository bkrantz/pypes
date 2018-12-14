

import signal
from pypes.util.async import AsyncManager, AsyncContextManager, RestartableGreenlet, BreakoutException
from pypes.globals.async import get_restart_pool
from pypes.testutils import funcs_tester, _test_func, BaseUnitTest
import gevent
import os

class TestAsyncManager(BaseUnitTest):

	def test_init(self):
		async = AsyncManager()
		self.assertEquals(async.is_stopped, True)
		async._AsyncManager__stopped.clear()
		self.assertEquals(async.is_stopped, False)
		os.kill(os.getpid(), signal.SIGINT)
		gevent.sleep(.1)
		self.assertEquals(async.is_stopped, True)

		async = AsyncManager()
		self.assertEquals(async.is_stopped, True)
		async._AsyncManager__stopped.clear()
		self.assertEquals(async.is_stopped, False)
		os.kill(os.getpid(), signal.SIGTERM)
		gevent.sleep(.1)
		self.assertEquals(async.is_stopped, True)

		self.assertEqual(isinstance(async._AsyncManager__managers, dict), True)
		self.assertEqual(len(async._AsyncManager__managers), 0)

	def test__AsyncManager__pop_stopping_threads(self):
		#test initially stopped
		MockAsyncManager = funcs_tester(clazz=AsyncManager, func_definitions={"sleep": None})
		async = MockAsyncManager()
		self.assertEquals(async.is_stopped, True)
		_test_func(self=self, obj=async, func_name="sleep", did=False, args=None, kwargs=None, count=0)
		async._AsyncManager__pop_stopping_threads()
		_test_func(self=self, obj=async, func_name="sleep", did=True, args=tuple(), kwargs=dict(), count=2)
		self.assertEquals(async.is_stopped, True)

		async = MockAsyncManager()
		MockEvent = funcs_tester(clazz=async._AsyncManager__stopped.__class__, func_definitions={"set":None,"clear":None})
		async._AsyncManager__stopped = MockEvent()
		async._AsyncManager__stopped._flag = True
		self.assertEquals(async.is_stopped, True)
		_test_func(self=self, obj=async._AsyncManager__stopped, func_name="set", did=False, args=None, kwargs=None, count=0)
		_test_func(self=self, obj=async._AsyncManager__stopped, func_name="clear", did=False, args=None, kwargs=None, count=0)
		_test_func(self=self, obj=async, func_name="sleep", did=False, args=None, kwargs=None, count=0)
		async._AsyncManager__pop_stopping_threads()
		_test_func(self=self, obj=async, func_name="sleep", did=True, args=tuple(), kwargs=dict(), count=2)
		_test_func(self=self, obj=async._AsyncManager__stopped, func_name="set", did=True, args=tuple(), kwargs=dict(), count=1)
		_test_func(self=self, obj=async._AsyncManager__stopped, func_name="clear", did=False, args=None, kwargs=None, count=0)
		self.assertEquals(async.is_stopped, True)

		#test initially running
		async = MockAsyncManager()
		async._AsyncManager__stopped._flag = False
		self.assertEquals(async.is_stopped, False)
		_test_func(self=self, obj=async, func_name="sleep", did=False, args=None, kwargs=None, count=0)
		async._AsyncManager__pop_stopping_threads()
		_test_func(self=self, obj=async, func_name="sleep", did=True, args=tuple(), kwargs=dict(), count=2)
		self.assertEquals(async.is_stopped, False)

		async = MockAsyncManager()
		async._AsyncManager__stopped = MockEvent()
		self.assertEquals(async.is_stopped, False)
		_test_func(self=self, obj=async._AsyncManager__stopped, func_name="set", did=False, args=None, kwargs=None, count=0)
		_test_func(self=self, obj=async._AsyncManager__stopped, func_name="clear", did=False, args=None, kwargs=None, count=0)
		_test_func(self=self, obj=async, func_name="sleep", did=False, args=None, kwargs=None, count=0)
		async._AsyncManager__pop_stopping_threads()
		_test_func(self=self, obj=async, func_name="sleep", did=True, args=tuple(), kwargs=dict(), count=2)
		_test_func(self=self, obj=async._AsyncManager__stopped, func_name="set", did=True, args=tuple(), kwargs=dict(), count=1)
		_test_func(self=self, obj=async._AsyncManager__stopped, func_name="clear", did=True, args=tuple(), kwargs=dict(), count=1)
		self.assertEquals(async.is_stopped, False)

	def test_add_context_manager(self):
		#test not AsyncManager manager
		async = AsyncManager()
		with self.assertRaises(AssertionError):
			async.add_context_manager(key="some random characters", manager="not a context manager")

		#test success while stopped
		MockAsyncManager = funcs_tester(clazz=AsyncManager, func_definitions={"_AsyncManager__try_start_single": None})
		async = MockAsyncManager()
		self.assertEquals(len(async._AsyncManager__managers), 0)
		self.assertEquals(async.is_stopped, True)
		_test_func(self=self, obj=async, func_name="_AsyncManager__try_start_single", did=False, args=None, kwargs=None, count=0)
		async.add_context_manager(key="some random characters", manager=AsyncContextManager())
		self.assertEquals(len(async._AsyncManager__managers), 1)
		_test_func(self=self, obj=async, func_name="_AsyncManager__try_start_single", did=False, args=None, kwargs=None, count=0)
		self.assertEquals(async.is_stopped, True)

		#test success while running
		MockAsyncManager = funcs_tester(clazz=AsyncManager, func_definitions={"_AsyncManager__try_start_single": None})
		async = MockAsyncManager()
		manager = AsyncContextManager()
		async._AsyncManager__stopped.clear()
		self.assertEquals(async.is_stopped, False)
		self.assertEquals(len(async._AsyncManager__managers), 0)
		_test_func(self=self, obj=async, func_name="_AsyncManager__try_start_single", did=False, args=None, kwargs=None, count=0)
		async.add_context_manager(key="some random characters", manager=manager)
		self.assertEquals(len(async._AsyncManager__managers), 1)
		_test_func(self=self, obj=async, func_name="_AsyncManager__try_start_single", did=True, args=tuple(), kwargs={"manager":manager}, count=1)
		self.assertEquals(async.is_stopped, False)
		
	def test_remove_context_manager(self):
		#test success while stopped
		MockAsyncManager = funcs_tester(clazz=AsyncManager, func_definitions={"_AsyncManager__try_stop_single": None,"_AsyncManager__pop_stopping_threads": None})
		async, manager = MockAsyncManager(), AsyncContextManager()
		self.assertEquals(async.is_stopped, True)
		self.assertEquals(len(async._AsyncManager__managers), 0)
		async.add_context_manager(key="1", manager=manager)
		self.assertEquals(len(async._AsyncManager__managers), 1)
		_test_func(self=self, obj=async, func_name="_AsyncManager__try_stop_single", did=False, args=None, kwargs=None, count=0)
		_test_func(self=self, obj=async, func_name="_AsyncManager__pop_stopping_threads", did=False, args=None, kwargs=None, count=0)
		async.remove_context_manager(key="1")
		_test_func(self=self, obj=async, func_name="_AsyncManager__try_stop_single", did=False, args=None, kwargs=None, count=0)
		_test_func(self=self, obj=async, func_name="_AsyncManager__pop_stopping_threads", did=False, args=None, kwargs=None, count=0)
		self.assertEquals(len(async._AsyncManager__managers), 0)
		self.assertEquals(async.is_stopped, True)

		#test success while running
		MockAsyncManager = funcs_tester(clazz=AsyncManager, func_definitions={"_AsyncManager__try_stop_single": None,"_AsyncManager__pop_stopping_threads": None})
		async, manager = MockAsyncManager(), AsyncContextManager()
		async._AsyncManager__stopped.clear()
		self.assertEquals(async.is_stopped, False)
		self.assertEquals(len(async._AsyncManager__managers), 0)
		async.add_context_manager(key="1", manager=manager)
		self.assertEquals(len(async._AsyncManager__managers), 1)
		_test_func(self=self, obj=async, func_name="_AsyncManager__try_stop_single", did=False, args=None, kwargs=None, count=0)
		_test_func(self=self, obj=async, func_name="_AsyncManager__pop_stopping_threads", did=False, args=None, kwargs=None, count=0)
		async.remove_context_manager(key="1")
		_test_func(self=self, obj=async, func_name="_AsyncManager__try_stop_single", did=True, args=tuple(), kwargs={"manager":manager}, count=1)
		_test_func(self=self, obj=async, func_name="_AsyncManager__pop_stopping_threads", did=True, args=tuple(), kwargs=dict(), count=1)
		self.assertEquals(len(async._AsyncManager__managers), 0)
		self.assertEquals(async.is_stopped, False)

		#test missing key while stopped
		MockAsyncManager = funcs_tester(clazz=AsyncManager, func_definitions={"_AsyncManager__try_stop_single": None,"_AsyncManager__pop_stopping_threads": None})
		async, manager = MockAsyncManager(), AsyncContextManager()
		self.assertEquals(async.is_stopped, True)
		self.assertEquals(len(async._AsyncManager__managers), 0)
		async.add_context_manager(key="1", manager=manager)
		self.assertEquals(len(async._AsyncManager__managers), 1)
		_test_func(self=self, obj=async, func_name="_AsyncManager__try_stop_single", did=False, args=None, kwargs=None, count=0)
		_test_func(self=self, obj=async, func_name="_AsyncManager__pop_stopping_threads", did=False, args=None, kwargs=None, count=0)
		async.remove_context_manager(key="2")
		_test_func(self=self, obj=async, func_name="_AsyncManager__try_stop_single", did=False, args=None, kwargs=None, count=0)
		_test_func(self=self, obj=async, func_name="_AsyncManager__pop_stopping_threads", did=False, args=None, kwargs=None, count=0)
		self.assertEquals(len(async._AsyncManager__managers), 1)
		self.assertEquals(async.is_stopped, True)

		#test missing key while running
		MockAsyncManager = funcs_tester(clazz=AsyncManager, func_definitions={"_AsyncManager__try_stop_single": None,"_AsyncManager__pop_stopping_threads": None})
		async, manager = MockAsyncManager(), AsyncContextManager()
		async._AsyncManager__stopped.clear()
		self.assertEquals(async.is_stopped, False)
		self.assertEquals(len(async._AsyncManager__managers), 0)
		async.add_context_manager(key="1", manager=manager)
		self.assertEquals(len(async._AsyncManager__managers), 1)
		_test_func(self=self, obj=async, func_name="_AsyncManager__try_stop_single", did=False, args=None, kwargs=None, count=0)
		_test_func(self=self, obj=async, func_name="_AsyncManager__pop_stopping_threads", did=False, args=None, kwargs=None, count=0)
		async.remove_context_manager(key="2")
		_test_func(self=self, obj=async, func_name="_AsyncManager__try_stop_single", did=False, args=None, kwargs=None, count=0)
		_test_func(self=self, obj=async, func_name="_AsyncManager__pop_stopping_threads", did=False, args=None, kwargs=None, count=0)
		self.assertEquals(len(async._AsyncManager__managers), 1)
		self.assertEquals(async.is_stopped, False)

	def test__AsyncManager__try_stop_single(self):
		#test manager is running
		async = AsyncManager()
		manager = AsyncContextManager()
		manager._AsyncContextManager__running.set()
		manager._AsyncContextManager__stop.clear()
		self.assertEqual(manager._AsyncContextManager__running.is_set(), True)
		self.assertEqual(manager._AsyncContextManager__stop.is_set(), False)
		async._AsyncManager__try_stop_single(manager=manager)
		self.assertEqual(manager._AsyncContextManager__running.is_set(), True)
		self.assertEqual(manager._AsyncContextManager__stop.is_set(), True)

		async = AsyncManager()
		manager = AsyncContextManager()
		manager._AsyncContextManager__running.set()
		manager._AsyncContextManager__stop.set()
		self.assertEqual(manager._AsyncContextManager__running.is_set(), True)
		self.assertEqual(manager._AsyncContextManager__stop.is_set(), True)
		async._AsyncManager__try_stop_single(manager=manager)
		self.assertEqual(manager._AsyncContextManager__running.is_set(), True)
		self.assertEqual(manager._AsyncContextManager__stop.is_set(), True)

		#test manager is not running
		async = AsyncManager()
		manager = AsyncContextManager()
		manager._AsyncContextManager__running.clear()
		manager._AsyncContextManager__stop.clear()
		self.assertEqual(manager._AsyncContextManager__running.is_set(), False)
		self.assertEqual(manager._AsyncContextManager__stop.is_set(), False)
		async._AsyncManager__try_stop_single(manager=manager)
		self.assertEqual(manager._AsyncContextManager__running.is_set(), False)
		self.assertEqual(manager._AsyncContextManager__stop.is_set(), False)

	def test__AsyncManager__try_start_single(self):
		#test manager is running
		MockAsyncManager = funcs_tester(clazz=AsyncManager, func_definitions={"_AsyncManager__single_start": None})
		async = MockAsyncManager()
		manager = AsyncContextManager()
		manager._AsyncContextManager__running.clear()
		self.assertEqual(manager._AsyncContextManager__running.is_set(), False)
		self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 0)
		async._AsyncManager__try_start_single(manager=manager)
		self.assertEqual(manager._AsyncContextManager__running.is_set(), False)
		self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 1)
		_test_func(self=self, obj=async, func_name="_AsyncManager__single_start", did=False, args=None, kwargs=None, count=0)
		async.sleep(0)
		_test_func(self=self, obj=async, func_name="_AsyncManager__single_start", did=True, args=tuple(), kwargs={"manager":manager}, count=1)

		#test manager is not running
		get_restart_pool().reset()
		async = MockAsyncManager()
		manager = AsyncContextManager()
		manager._AsyncContextManager__running.set()
		self.assertEqual(manager._AsyncContextManager__running.is_set(), True)
		self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 0)
		async._AsyncManager__try_start_single(manager=manager)
		self.assertEqual(manager._AsyncContextManager__running.is_set(), True)
		self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 0)
		_test_func(self=self, obj=async, func_name="_AsyncManager__single_start", did=False, args=None, kwargs=None, count=0)
		async.sleep(0)
		_test_func(self=self, obj=async, func_name="_AsyncManager__single_start", did=False, args=None, kwargs=None, count=0)

	def test__AsyncManager__single_start(self):
		async = AsyncManager()
		manager = AsyncContextManager()
		self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 0)
		get_restart_pool().spawn(run=async._AsyncManager__single_start, manager=manager, graceful_restart=False, irregular_restart=False)
		self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 1)
		self.assertEqual(manager.is_running(), False)
		async.sleep()
		self.assertEqual(manager.is_running(), True)
		async.trigger_stop()
		self.assertEqual(manager.is_running(), True)
		async.sleep()
		self.assertEqual(manager.is_running(), True)
		async._AsyncManager__stopped.clear()
		manager.trigger_stop()
		self.assertEqual(manager.is_running(), True)
		async.sleep()
		self.assertEqual(manager.is_running(), True)
		async.trigger_stop()
		self.assertEqual(manager.is_running(), True)
		async.sleep()
		self.assertEqual(manager.is_running(), False)
		self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 1)
		async.sleep()
		self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 0)

	def test_stop_funcs(self):
		async = AsyncManager()
		self.assertEqual(async.is_stopped, True)
		async._AsyncManager__stopped.clear()
		self.assertEqual(async.is_stopped, False)
		async.trigger_stop()
		self.assertEqual(async.is_stopped, True)

		async._AsyncManager__stopped.clear()
		self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 0)
		get_restart_pool().spawn(run=async.wait_for_stop, graceful_restart=False, irregular_restart=False)
		self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 1)
		async.sleep()
		async.sleep()
		self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 1)
		async.trigger_stop()
		async.sleep()
		async.sleep()
		self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 0)

	def test_sleep(self):
		import time
		async = AsyncManager()
		start = time.time()
		async.sleep(.7)
		end = time.time()
		elapsed = end - start
		self.assertGreater(elapsed, .6)
		self.assertLess(elapsed, .8)

	def test_context_manager(self):
		#expected usage
		async = AsyncManager()
		self.assertEqual(len(async._AsyncManager__managers), 0)
		self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 0)
		async.add_context_manager(key="1", manager=AsyncContextManager())
		async.add_context_manager(key="2", manager=AsyncContextManager())
		async.add_context_manager(key="3", manager=AsyncContextManager())
		self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 0)
		self.assertEqual(len(async._AsyncManager__managers), 3)
		for manager in async._AsyncManager__managers.itervalues():
			self.assertEqual(manager.is_running(), False)
		with async:
			self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 3)
			for manager in async._AsyncManager__managers.itervalues():
				self.assertEqual(manager.is_running(), False)
			async.sleep() #allows managers to start  # typically would be a block here
			self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 3)
			for manager in async._AsyncManager__managers.itervalues():
				self.assertEqual(manager.is_running(), True)
		self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 0)
		for manager in async._AsyncManager__managers.itervalues():
			self.assertEqual(manager.is_running(), False)

		#restart restartablity
		self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 0)
		self.assertEqual(len(async._AsyncManager__managers), 3)
		for manager in async._AsyncManager__managers.itervalues():
			self.assertEqual(manager.is_running(), False)
		with async:
			self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 3)
			for manager in async._AsyncManager__managers.itervalues():
				self.assertEqual(manager.is_running(), False)
			async.sleep() #allows managers to start  # typically would be a block here
			self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 3)
			for manager in async._AsyncManager__managers.itervalues():
				self.assertEqual(manager.is_running(), True)
		self.assertEqual(len(get_restart_pool()._RestartPool__greenlet_dict), 0)
		for manager in async._AsyncManager__managers.itervalues():
			self.assertEqual(manager.is_running(), False)

class TestRestartableGreenlet(BaseUnitTest):
	def test_init(self):
		def run_test(): pass
		class Logger(object): pass
		pool = gevent.pool.Pool(greenlet_class=RestartableGreenlet)

		#missing run param
		with self.assertRaises(TypeError):
			greenlet = pool.spawn()

		#defaults
		greenlet = pool.spawn(run=run_test,)
		self.assertEqual(isinstance(greenlet, RestartableGreenlet), True)
		self.assertEqual(greenlet.rg_run, run_test)
		self.assertEqual(greenlet.rg_graceful_restart, True)
		self.assertEqual(greenlet.rg_irregular_restart, True)
		self.assertEqual(greenlet.rg_logger, None)
		self.assertNotEqual(greenlet.rg_key, None)
		self.assertEqual(greenlet.rg_args, tuple())
		self.assertEqual(greenlet.rg_kwargs, dict())
		self.assertEqual(greenlet._RestartableGreenlet__running, True)

		#inits
		logger = Logger()
		greenlet = pool.spawn(run=run_test, graceful_restart=False, irregular_restart=False, logger=logger, key="something", other="test")
		self.assertEqual(isinstance(greenlet, RestartableGreenlet), True)
		self.assertEqual(greenlet.rg_run, run_test)
		self.assertEqual(greenlet.rg_graceful_restart, False)
		self.assertEqual(greenlet.rg_irregular_restart, False)
		self.assertEqual(greenlet.rg_logger, logger)
		self.assertEqual(greenlet.rg_key, "something")
		self.assertEqual(greenlet.rg_args, tuple())
		self.assertEqual(greenlet.rg_kwargs, {"other": "test"})
		self.assertEqual(greenlet._RestartableGreenlet__running, True)

		greenlet.running = False
		self.assertEqual(greenlet._RestartableGreenlet__running, greenlet.running)
		greenlet.running = True
		self.assertEqual(greenlet._RestartableGreenlet__running, greenlet.running)

	def test__report_error(self):
		def run_test(): pass
		pool = gevent.pool.Pool(greenlet_class=RestartableGreenlet)
		greenlet = pool.spawn(run=run_test,)
		greenlet._report_error(exc_info=[BreakoutException, BreakoutException(), 0])
		greenlet._report_error(exc_info=[Exception, Exception(), 0])

	def test_kill(self):
		pass


