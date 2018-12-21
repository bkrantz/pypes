

import signal
from pypes.util.async import AsyncManager, AsyncContextManager, RestartableGreenlet, KilledException, sleep, RestartPool, timestamp
from pypes.globals.async import get_restart_pool, DEFAULT_SLEEP_INTERVAL, get_async_manager, _override_async_manager, _override_restart_pool
from pypes.testutils import funcs_tester, _test_func, BaseUnitTest, _test_meta_func_error
from pypes.util import RedirectStdStreams
import gevent
import os
from pypes.metas.async import IgnoreDerivativesMeta
import gevent.exceptions.LoopExit as LoopExit

class TestSleep(BaseUnitTest):
	def test_sleep(self):
		import time
		start = time.time()
		sleep(.2)
		end = time.time()
		elapsed = end - start
		self.assertGreater(elapsed, .1)
		self.assertLess(elapsed, .3)

class TestTimestamp(BaseUnitTest):
	def test_timestamp(self):
		start = timestamp()
		gevent.sleep(.2)
		end = timestamp()
		elapsed = end - start
		self.assertGreater(elapsed, .1)
		self.assertLess(elapsed, .3)

class TestKilledException(BaseUnitTest):
	def test_meta(self):
		with self.assertRaises(TypeError):
			class Deriv(KilledException):
				pass

class TestAsyncManager(BaseUnitTest):

	def test_meta(self):
		with self.assertRaises(TypeError):
			class Deriv(AsyncManager):
				pass

	def test_init(self):
		_override_async_manager(manager=AsyncManager())
		self.assertEquals(get_async_manager().is_stopped, True)
		get_async_manager()._AsyncManager__stopped.clear()
		self.assertEquals(get_async_manager().is_stopped, False)
		os.kill(os.getpid(), signal.SIGINT)
		sleep(duration=.1)
		self.assertEquals(get_async_manager().is_stopped, True)

		_override_async_manager(manager=AsyncManager())
		self.assertEquals(get_async_manager().is_stopped, True)
		get_async_manager()._AsyncManager__stopped.clear()
		self.assertEquals(get_async_manager().is_stopped, False)
		os.kill(os.getpid(), signal.SIGTERM)
		sleep(duration=.1)
		self.assertEquals(get_async_manager().is_stopped, True)

		self.assertEqual(isinstance(get_async_manager()._AsyncManager__managers, dict), True)
		self.assertEqual(len(get_async_manager()._AsyncManager__managers), 0)

	def test__AsyncManager__pop_stopping_threads(self):
		#test initially stopped
		MockAsyncManager = funcs_tester(clazz=AsyncManager, func_definitions={"sleep": None})
		_override_async_manager(manager=MockAsyncManager())
		self.assertEquals(get_async_manager().is_stopped, True)
		get_async_manager()._AsyncManager__pop_stopping_threads()
		self.assertEquals(get_async_manager().is_stopped, True)

		_override_async_manager(manager=MockAsyncManager())
		MockEvent = funcs_tester(clazz=get_async_manager()._AsyncManager__stopped.__class__, func_definitions={"set":None,"clear":None})
		get_async_manager()._AsyncManager__stopped = MockEvent()
		get_async_manager()._AsyncManager__stopped._flag = True
		self.assertEquals(get_async_manager().is_stopped, True)
		_test_func(self=self, obj=get_async_manager()._AsyncManager__stopped, func_name="set", did=False, args=None, kwargs=None, count=0)
		_test_func(self=self, obj=get_async_manager()._AsyncManager__stopped, func_name="clear", did=False, args=None, kwargs=None, count=0)
		get_async_manager()._AsyncManager__pop_stopping_threads()
		_test_func(self=self, obj=get_async_manager()._AsyncManager__stopped, func_name="set", did=True, args=tuple(), kwargs=dict(), count=1)
		_test_func(self=self, obj=get_async_manager()._AsyncManager__stopped, func_name="clear", did=False, args=None, kwargs=None, count=0)
		self.assertEquals(get_async_manager().is_stopped, True)

		#test initially running
		_override_async_manager(manager=MockAsyncManager())
		get_async_manager()._AsyncManager__stopped._flag = False
		self.assertEquals(get_async_manager().is_stopped, False)
		get_async_manager()._AsyncManager__pop_stopping_threads()
		self.assertEquals(get_async_manager().is_stopped, False)

		_override_async_manager(manager=MockAsyncManager())
		get_async_manager()._AsyncManager__stopped = MockEvent()
		self.assertEquals(get_async_manager().is_stopped, False)
		_test_func(self=self, obj=get_async_manager()._AsyncManager__stopped, func_name="set", did=False, args=None, kwargs=None, count=0)
		_test_func(self=self, obj=get_async_manager()._AsyncManager__stopped, func_name="clear", did=False, args=None, kwargs=None, count=0)
		get_async_manager()._AsyncManager__pop_stopping_threads()
		_test_func(self=self, obj=get_async_manager()._AsyncManager__stopped, func_name="set", did=True, args=tuple(), kwargs=dict(), count=1)
		_test_func(self=self, obj=get_async_manager()._AsyncManager__stopped, func_name="clear", did=True, args=tuple(), kwargs=dict(), count=1)
		self.assertEquals(get_async_manager().is_stopped, False)

	def test_add_context_manager(self):
		#test not AsyncManager manager
		_override_async_manager(manager=AsyncManager())
		with self.assertRaises(AssertionError):
			get_async_manager().add_context_manager(key="some random characters", manager="not a context manager")

		#test success while stopped
		MockAsyncManager = funcs_tester(clazz=AsyncManager, func_definitions={"_AsyncManager__try_start_single": None})
		_override_async_manager(manager=MockAsyncManager())
		self.assertEquals(len(get_async_manager()._AsyncManager__managers), 0)
		manager = AsyncContextManager()
		self.assertEquals(len(get_async_manager()._AsyncManager__managers), 1)
		self.assertEquals(get_async_manager().is_stopped, True)
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__try_start_single", did=False, args=None, kwargs=None, count=0)
		get_async_manager().add_context_manager(key="some random characters", manager=manager)
		self.assertEquals(len(get_async_manager()._AsyncManager__managers), 2)
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__try_start_single", did=False, args=None, kwargs=None, count=0)
		self.assertEquals(get_async_manager().is_stopped, True)
		managers = get_async_manager()._AsyncManager__managers.values()
		self.assertEqual(managers[0], managers[1])

		#test success while running
		MockAsyncManager = funcs_tester(clazz=AsyncManager, func_definitions={"_AsyncManager__try_start_single": None})
		_override_async_manager(manager=MockAsyncManager())
		manager = AsyncContextManager()
		get_async_manager()._AsyncManager__stopped.clear()
		self.assertEquals(get_async_manager().is_stopped, False)
		self.assertEquals(len(get_async_manager()._AsyncManager__managers), 1)
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__try_start_single", did=False, args=None, kwargs=None, count=0)
		get_async_manager().add_context_manager(key="some random characters", manager=manager)
		self.assertEquals(len(get_async_manager()._AsyncManager__managers), 2)
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__try_start_single", did=True, args=tuple(), kwargs={"manager":manager}, count=1)
		self.assertEquals(get_async_manager().is_stopped, False)
		
	def test_remove_context_manager(self):
		#test success while stopped
		MockAsyncManager = funcs_tester(clazz=AsyncManager, func_definitions={"_AsyncManager__try_stop_single": None,"_AsyncManager__pop_stopping_threads": None})
		manager = AsyncContextManager()
		_override_async_manager(manager=MockAsyncManager())
		self.assertEquals(get_async_manager().is_stopped, True)
		self.assertEquals(len(get_async_manager()._AsyncManager__managers), 0)
		get_async_manager().add_context_manager(key="1", manager=manager)
		self.assertEquals(len(get_async_manager()._AsyncManager__managers), 1)
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__try_stop_single", did=False, args=None, kwargs=None, count=0)
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__pop_stopping_threads", did=False, args=None, kwargs=None, count=0)
		get_async_manager().remove_context_manager(key="1")
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__try_stop_single", did=False, args=None, kwargs=None, count=0)
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__pop_stopping_threads", did=False, args=None, kwargs=None, count=0)
		self.assertEquals(len(get_async_manager()._AsyncManager__managers), 0)
		self.assertEquals(get_async_manager().is_stopped, True)

		#test success while running
		MockAsyncManager = funcs_tester(clazz=AsyncManager, func_definitions={"_AsyncManager__try_stop_single": None,"_AsyncManager__pop_stopping_threads": None})
		manager = AsyncContextManager()
		_override_async_manager(manager=MockAsyncManager())
		get_async_manager()._AsyncManager__stopped.clear()
		self.assertEquals(get_async_manager().is_stopped, False)
		self.assertEquals(len(get_async_manager()._AsyncManager__managers), 0)
		get_async_manager().add_context_manager(key="1", manager=manager)
		self.assertEquals(len(get_async_manager()._AsyncManager__managers), 1)
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__try_stop_single", did=False, args=None, kwargs=None, count=0)
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__pop_stopping_threads", did=False, args=None, kwargs=None, count=0)
		get_async_manager().remove_context_manager(key="1")
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__try_stop_single", did=True, args=tuple(), kwargs={"manager":manager}, count=1)
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__pop_stopping_threads", did=True, args=tuple(), kwargs=dict(), count=1)
		self.assertEquals(len(get_async_manager()._AsyncManager__managers), 0)
		self.assertEquals(get_async_manager().is_stopped, False)

		#test missing key while stopped
		MockAsyncManager = funcs_tester(clazz=AsyncManager, func_definitions={"_AsyncManager__try_stop_single": None,"_AsyncManager__pop_stopping_threads": None})
		manager = AsyncContextManager()
		_override_async_manager(manager=MockAsyncManager())
		self.assertEquals(get_async_manager().is_stopped, True)
		self.assertEquals(len(get_async_manager()._AsyncManager__managers), 0)
		get_async_manager().add_context_manager(key="1", manager=manager)
		self.assertEquals(len(get_async_manager()._AsyncManager__managers), 1)
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__try_stop_single", did=False, args=None, kwargs=None, count=0)
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__pop_stopping_threads", did=False, args=None, kwargs=None, count=0)
		get_async_manager().remove_context_manager(key="2")
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__try_stop_single", did=False, args=None, kwargs=None, count=0)
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__pop_stopping_threads", did=False, args=None, kwargs=None, count=0)
		self.assertEquals(len(get_async_manager()._AsyncManager__managers), 1)
		self.assertEquals(get_async_manager().is_stopped, True)

		#test missing key while running
		MockAsyncManager = funcs_tester(clazz=AsyncManager, func_definitions={"_AsyncManager__try_stop_single": None,"_AsyncManager__pop_stopping_threads": None})
		manager = AsyncContextManager()
		_override_async_manager(manager=MockAsyncManager())
		get_async_manager()._AsyncManager__stopped.clear()
		self.assertEquals(get_async_manager().is_stopped, False)
		self.assertEquals(len(get_async_manager()._AsyncManager__managers), 0)
		get_async_manager().add_context_manager(key="1", manager=manager)
		self.assertEquals(len(get_async_manager()._AsyncManager__managers), 1)
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__try_stop_single", did=False, args=None, kwargs=None, count=0)
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__pop_stopping_threads", did=False, args=None, kwargs=None, count=0)
		get_async_manager().remove_context_manager(key="2")
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__try_stop_single", did=False, args=None, kwargs=None, count=0)
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__pop_stopping_threads", did=False, args=None, kwargs=None, count=0)
		self.assertEquals(len(get_async_manager()._AsyncManager__managers), 1)
		self.assertEquals(get_async_manager().is_stopped, False)

	def test__AsyncManager__try_stop_single(self):
		#test manager is running
		_override_async_manager(manager=AsyncManager())
		manager = AsyncContextManager()
		manager._AsyncContextManager__running.set()
		manager._AsyncContextManager__stopped.clear()
		self.assertEqual(manager._AsyncContextManager__running.is_set(), True)
		self.assertEqual(manager._AsyncContextManager__stopped.is_set(), False)
		get_async_manager()._AsyncManager__try_stop_single(manager=manager)
		self.assertEqual(manager._AsyncContextManager__running.is_set(), True)
		self.assertEqual(manager._AsyncContextManager__stopped.is_set(), True)

		_override_async_manager(manager=AsyncManager())
		manager = AsyncContextManager()
		manager._AsyncContextManager__running.set()
		manager._AsyncContextManager__stopped.set()
		self.assertEqual(manager._AsyncContextManager__running.is_set(), True)
		self.assertEqual(manager._AsyncContextManager__stopped.is_set(), True)
		get_async_manager()._AsyncManager__try_stop_single(manager=manager)
		self.assertEqual(manager._AsyncContextManager__running.is_set(), True)
		self.assertEqual(manager._AsyncContextManager__stopped.is_set(), True)

		#test manager is not running
		_override_async_manager(manager=AsyncManager())
		manager = AsyncContextManager()
		manager._AsyncContextManager__running.clear()
		manager._AsyncContextManager__stopped.clear()
		self.assertEqual(manager._AsyncContextManager__running.is_set(), False)
		self.assertEqual(manager._AsyncContextManager__stopped.is_set(), False)
		get_async_manager()._AsyncManager__try_stop_single(manager=manager)
		self.assertEqual(manager._AsyncContextManager__running.is_set(), False)
		self.assertEqual(manager._AsyncContextManager__stopped.is_set(), False)

	def test__AsyncManager__try_start_single(self):
		#test manager is running
		MockAsyncManager = funcs_tester(clazz=AsyncManager, func_definitions={"_AsyncManager__single_start": None})
		_override_async_manager(manager=MockAsyncManager())
		manager = AsyncContextManager()
		manager._AsyncContextManager__running.clear()
		self.assertEqual(manager._AsyncContextManager__running.is_set(), False)
		self.assertEqual(len(get_restart_pool().greenlets), 0)
		get_async_manager()._AsyncManager__try_start_single(manager=manager)
		self.assertEqual(manager._AsyncContextManager__running.is_set(), False)
		self.assertEqual(len(get_restart_pool().greenlets), 1)
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__single_start", did=False, args=None, kwargs=None, count=0)
		sleep()
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__single_start", did=True, args=tuple(), kwargs={"manager":manager}, count=1)

		#test manager is not running
		get_restart_pool().kill()
		_override_async_manager(manager=MockAsyncManager())
		manager = AsyncContextManager()
		manager._AsyncContextManager__running.set()
		self.assertEqual(manager._AsyncContextManager__running.is_set(), True)
		self.assertEqual(len(get_restart_pool().greenlets), 0)
		get_async_manager()._AsyncManager__try_start_single(manager=manager)
		self.assertEqual(manager._AsyncContextManager__running.is_set(), True)
		self.assertEqual(len(get_restart_pool().greenlets), 0)
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__single_start", did=False, args=None, kwargs=None, count=0)
		sleep()
		_test_func(self=self, obj=get_async_manager(), func_name="_AsyncManager__single_start", did=False, args=None, kwargs=None, count=0)

	def test__AsyncManager__single_start(self):
		_override_async_manager(manager=AsyncManager())
		manager = AsyncContextManager()
		self.assertEqual(len(get_restart_pool().greenlets), 0)
		get_restart_pool().spawn(run=get_async_manager()._AsyncManager__single_start, manager=manager, greenlet_manager=manager, graceful_restart=False, rough_restart=False)
		self.assertEqual(len(get_restart_pool().greenlets), 1)
		self.assertEqual(manager.is_running(), False)
		sleep()
		self.assertEqual(manager.is_running(), True)
		get_async_manager().trigger_stop()
		self.assertEqual(manager.is_running(), True)
		sleep()
		self.assertEqual(manager.is_running(), True)
		get_async_manager()._AsyncManager__stopped.clear()
		manager.trigger_stop()
		self.assertEqual(manager.is_running(), True)
		sleep()
		self.assertEqual(manager.is_running(), True)
		get_async_manager().trigger_stop()
		self.assertEqual(manager.is_running(), True)
		self.assertEqual(len(get_restart_pool().greenlets), 1)
		sleep(); sleep()
		self.assertEqual(len(get_restart_pool().greenlets), 0)

	def test_stop_funcs(self):
		_override_async_manager(manager=AsyncManager())
		self.assertEqual(get_async_manager().is_stopped, True)
		get_async_manager()._AsyncManager__stopped.clear()
		self.assertEqual(get_async_manager().is_stopped, False)
		get_async_manager().trigger_stop()
		self.assertEqual(get_async_manager().is_stopped, True)

		get_async_manager()._AsyncManager__stopped.clear()
		self.assertEqual(len(get_restart_pool().greenlets), 0)
		manager = AsyncContextManager()
		self.assertEqual(len(get_restart_pool().greenlets), 1)
		get_restart_pool().spawn(run=get_async_manager().wait_for_stop, greenlet_manager=manager, graceful_restart=False, rough_restart=False)
		self.assertEqual(len(get_restart_pool().greenlets), 2)
		sleep(); sleep()
		self.assertEqual(len(get_restart_pool().greenlets), 2)
		get_async_manager().trigger_stop()
		sleep(); sleep()
		self.assertEqual(len(get_restart_pool().greenlets), 1)

	def test_context_manager(self):
		#expected usage
		_override_async_manager(manager=AsyncManager())
		self.assertEqual(len(get_async_manager()._AsyncManager__managers), 0)
		self.assertEqual(len(get_restart_pool().greenlets), 0)
		AsyncContextManager(async_hidden_key="1"); AsyncContextManager(async_hidden_key="2"); AsyncContextManager(async_hidden_key="3")
		self.assertEqual(len(get_restart_pool().greenlets), 0)
		self.assertEqual(len(get_async_manager()._AsyncManager__managers), 3)
		for manager in get_async_manager()._AsyncManager__managers.itervalues():
			self.assertEqual(manager.is_running(), False)
		with get_async_manager():
			self.assertEqual(len(get_restart_pool().greenlets), 3)
			for manager in get_async_manager()._AsyncManager__managers.itervalues():
				self.assertEqual(manager.is_running(), False)
			sleep() #allows managers to start  # typically would be a block here
			self.assertEqual(len(get_restart_pool().greenlets), 3)
			for manager in get_async_manager()._AsyncManager__managers.itervalues():
				self.assertEqual(manager.is_running(), True)
			get_async_manager().trigger_stop()
		self.assertEqual(len(get_restart_pool().greenlets), 0)
		self.assertEqual(len(get_restart_pool().greenlets), 0)
		for manager in get_async_manager()._AsyncManager__managers.itervalues():
			self.assertEqual(manager.is_running(), False)

		#restart restartablity
		self.assertEqual(len(get_restart_pool().greenlets), 0)
		self.assertEqual(len(get_async_manager()._AsyncManager__managers), 3)
		for manager in get_async_manager()._AsyncManager__managers.itervalues():
			self.assertEqual(manager.is_running(), False)
		with get_async_manager():
			self.assertEqual(len(get_restart_pool().greenlets), 3)
			for manager in get_async_manager()._AsyncManager__managers.itervalues():
				self.assertEqual(manager.is_running(), False)
			sleep() #allows managers to start  # typically would be a block here
			self.assertEqual(len(get_restart_pool().greenlets), 3)
			for manager in get_async_manager()._AsyncManager__managers.itervalues():
				self.assertEqual(manager.is_running(), True)
			get_async_manager().trigger_stop()
		self.assertEqual(len(get_restart_pool().greenlets), 0)
		for manager in get_async_manager()._AsyncManager__managers.itervalues():
			self.assertEqual(manager.is_running(), False)

		with self.assertRaises(LoopExit):
			with get_async_manager():
				pass

class TestRestartableGreenlet(BaseUnitTest):

	def test_meta(self):
		with self.assertRaises(TypeError):
			class Deriv(RestartableGreenlet):
				pass

	def test_init(self):
		def run_test(*args, **kwargs): pass
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
		self.assertEqual(greenlet.rg_rough_restart, True)
		self.assertEqual(greenlet.rg_logger, None)
		self.assertEqual(greenlet.rg_args, tuple())
		self.assertEqual(greenlet.rg_kwargs, dict())
		self.assertEqual(greenlet.running, True)

		#inits
		logger = Logger()
		greenlet = pool.spawn(run=run_test, graceful_restart=False, rough_restart=False, logger=logger, other="test")
		self.assertEqual(isinstance(greenlet, RestartableGreenlet), True)
		self.assertEqual(greenlet.rg_run, run_test)
		self.assertEqual(greenlet.rg_graceful_restart, False)
		self.assertEqual(greenlet.rg_rough_restart, False)
		self.assertEqual(greenlet.rg_logger, logger)
		self.assertEqual(greenlet.rg_args, tuple())
		self.assertEqual(greenlet.rg_kwargs, {"other": "test"})
		self.assertEqual(greenlet.running, True)

		sleep()
		self.assertEqual(greenlet.running, False)

		pool.kill()
	def test__report_error(self):
		def run_test(): pass
		pool = gevent.pool.Pool(greenlet_class=RestartableGreenlet)
		greenlet = pool.spawn(run=run_test,)
		streamer = RedirectStdStreams()
		with streamer:
			greenlet._report_error(exc_info=[BreakoutException, BreakoutException(), 0])
		self.assertEqual(len(streamer.stderr), 0)
		with streamer:
			greenlet._report_error(exc_info=[Exception, Exception(), 0])
		self.assertNotEqual(len(streamer.stderr), 0)

	def test_kill(self):
		def callback(greenlet): self.assertEqual(isinstance(greenlet.exception, BreakoutException), True)
		def run_test(*args, **kwargs): sleep()
		pool = gevent.pool.Pool(greenlet_class=RestartableGreenlet)
		pool.kill()
		self.assertEqual(len(pool.greenlets), 0)
		greenlet = pool.spawn(run=run_test,)
		self.assertEqual(len(pool.greenlets), 1)
		greenlet.link_exception(callback=callback)
		sleep()
		self.assertEqual(len(pool.greenlets), 1)
		pool.kill()
		self.assertEqual(len(pool.greenlets), 0)


class TestRestartPool(BaseUnitTest):

	def test_meta(self):
		with self.assertRaises(TypeError):
			class Deriv(RestartPool):
				pass

	def test_init(self):
		#defaults
		pool = RestartPool()
		self.assertEqual(pool.sleep_interval, DEFAULT_SLEEP_INTERVAL)
		self.assertEqual(pool.graceful_restart, True)
		self.assertEqual(pool.rough_restart, True)
		self.assertEqual(pool.logger, None)
		self.assertEqual(pool.greenlet_class, RestartableGreenlet)

		#overrides
		pool = RestartPool(sleep_interval=2, graceful_restart=False, rough_restart=False, logger=7, greenlet_class=gevent.greenlet.Greenlet)
		self.assertEqual(pool.sleep_interval, 2)
		self.assertEqual(pool.graceful_restart, False)
		self.assertEqual(pool.rough_restart, False)
		self.assertEqual(pool.logger, 7)
		self.assertEqual(pool.greenlet_class, RestartableGreenlet)

	def test_spawn(self):
		def test_func(*args, **kwargs): pass
		#instance
		pool = RestartPool()
		greenlet = pool.spawn(run=test_func)
		self.assertEqual(isinstance(greenlet, RestartableGreenlet), True)
		pool.kill()
		pool = RestartPool(greenlet_class=gevent.greenlet.Greenlet)
		greenlet = pool.spawn(run=test_func)
		self.assertEqual(isinstance(greenlet, RestartableGreenlet), True)
		pool.kill()

		#defaults
		pool = RestartPool()
		greenlet = pool.spawn(run=test_func)
		self.assertEqual(greenlet.rg_graceful_restart, True)
		self.assertEqual(greenlet.rg_rough_restart, True)
		self.assertEqual(greenlet.rg_logger, None)
		pool.kill()

		pool = RestartPool(graceful_restart=False, rough_restart=False, logger=7)
		greenlet = pool.spawn(run=test_func)
		self.assertEqual(greenlet.rg_graceful_restart, False)
		self.assertEqual(greenlet.rg_rough_restart, False)
		self.assertEqual(greenlet.rg_logger, 7)
		pool.kill()

		#overrides
		pool = RestartPool()
		greenlet = pool.spawn(run=test_func, graceful_restart=False, rough_restart=False, logger=7)
		self.assertEqual(greenlet.rg_graceful_restart, False)
		self.assertEqual(greenlet.rg_rough_restart, False)
		self.assertEqual(greenlet.rg_logger, 7)
		pool.kill()

		pool = RestartPool(graceful_restart=False, rough_restart=False, logger=7)
		greenlet = pool.spawn(run=test_func, graceful_restart=True, rough_restart=True, logger=8)
		self.assertEqual(greenlet.rg_graceful_restart, True)
		self.assertEqual(greenlet.rg_rough_restart, True)
		self.assertEqual(greenlet.rg_logger, 8)
		pool.kill()

		#test links
		pool = RestartPool()
		greenlet = pool.spawn(run=test_func, graceful_restart=False, rough_restart=False, logger=7)
		self.assertEqual(len(greenlet._links), 3)  #default, graceful, and irregular links
		pool.kill()


	def test_respawn_greenlet(self):
		def test_func(*args, **kwargs): pass
		pool = RestartPool()
		greenlet1 = pool.spawn(run=test_func, graceful_restart=False, logger=9, some_kwarg="some_val")
		greenlet2 = pool.respawn_greenlet(greenlet=greenlet1)

		self.assertNotEqual(greenlet1, greenlet2)
		self.assertEqual(greenlet1.rg_run, greenlet2.rg_run)
		self.assertEqual(greenlet1.rg_graceful_restart, greenlet2.rg_graceful_restart)
		self.assertEqual(greenlet1.rg_rough_restart, greenlet2.rg_rough_restart)
		self.assertEqual(greenlet1.rg_logger, greenlet2.rg_logger)
		self.assertEqual(greenlet1.rg_args, greenlet2.rg_args)
		self.assertEqual(greenlet1.rg_kwargs, greenlet2.rg_kwargs)
		pool.kill()

	def test__RestartPool__graceful_termination(self):
		#successful restart
		def test_func(*args, **kwargs): pass
		pool = RestartPool()
		self.assertEqual(len(pool.greenlets), 0)
		greenlet = pool.spawn(run=test_func)
		self.assertEqual(len(pool.greenlets), 1)
		self.assertEqual(list(pool.greenlets)[0], greenlet)
		self.assertEqual(greenlet.rg_graceful_restart, True)
		sleep()
		self.assertEqual(len(pool.greenlets), 1)
		self.assertNotEqual(list(pool.greenlets)[0], greenlet)
		self.assertEqual(greenlet.rg_graceful_restart, True)
		pool.kill()

		#not configured restart
		pool = RestartPool()
		self.assertEqual(len(pool.greenlets), 0)
		greenlet = pool.spawn(run=test_func, graceful_restart=False)
		self.assertEqual(len(pool.greenlets), 1)
		self.assertEqual(list(pool.greenlets)[0], greenlet)
		self.assertEqual(greenlet.rg_graceful_restart, False)
		sleep()
		self.assertEqual(len(pool.greenlets), 0)
		pool.kill()

	def test__RestartPool__irregular_termination(self):
		#successful restart
		def test_func(*args, **kwargs): sleep(); raise Exception()
		pool = RestartPool()
		self.assertEqual(len(pool.greenlets), 0)
		greenlet = pool.spawn(run=test_func, suppress_std=True)
		self.assertEqual(len(pool.greenlets), 1)
		self.assertEqual(list(pool.greenlets)[0], greenlet)
		self.assertEqual(greenlet.rg_rough_restart, True)
		sleep(); sleep()
		self.assertEqual(len(pool.greenlets), 0)
		sleep()
		self.assertEqual(len(pool.greenlets), 1)
		self.assertNotEqual(list(pool.greenlets)[0], greenlet)
		self.assertEqual(greenlet.rg_rough_restart, True)
		pool.kill()

		#not configured restart
		pool = RestartPool()
		self.assertEqual(len(pool.greenlets), 0)
		greenlet = pool.spawn(run=test_func, rough_restart=False, suppress_std=True)
		self.assertEqual(len(pool.greenlets), 1)
		self.assertEqual(list(pool.greenlets)[0], greenlet)
		self.assertEqual(greenlet.rg_rough_restart, False)
		sleep(); sleep()
		self.assertEqual(len(pool.greenlets), 0)
		sleep()
		self.assertEqual(len(pool.greenlets), 0)
		pool.kill()

	def test_killone(self):
		def test_func(): sleep()
		def new_irregular(greenlet):
			self.assertEqual(isinstance(greenlet.exception, BreakoutException), True)
		pool = RestartPool()
		pool._RestartPool__irregular_termination = new_irregular
		greenlet = pool.spawn(run=test_func)
		self.assertEqual(len(pool.greenlets), 1)
		pool.killone(greenlet=greenlet)
		self.assertEqual(len(pool.greenlets), 1)
		sleep()
		self.assertEqual(len(pool.greenlets), 0)

	def test_kill(self):
		def test_func(): sleep()
		def new_irregular(greenlet):
			self.assertEqual(isinstance(greenlet.exception, BreakoutException), True)
		pool = RestartPool()
		pool._RestartPool__irregular_termination = new_irregular
		greenlet = pool.spawn(run=test_func)
		greenlet = pool.spawn(run=test_func)
		self.assertEqual(len(pool.greenlets), 2)
		pool.kill()
		self.assertEqual(len(pool.greenlets), 2)
		sleep()
		self.assertEqual(len(pool.greenlets), 0)

class TestAsyncContextManager(BaseUnitTest):

	def test_meta(self):
		#baseline
		GoodClazz = type('GoodClazz', (AsyncContextManager,), {"start":lambda x: x, "stop":lambda x: x})

		#_test_meta_func_error(self=self, root_clazz=AsyncContextManager) #missing start and stop
		#_test_meta_func_error(self=self, root_clazz=AsyncContextManager, func_names=["start"]) #missing stop
		#_test_meta_func_error(self=self, root_clazz=AsyncContextManager, func_names=["stop"]) #missing start
		#func override tests
		#_test_meta_func_error(self=self, root_clazz=GoodClazz, func_names=["_Actor__connect_queue"]) 
		#_test_meta_func_error(self=self, root_clazz=GoodClazz, func_names=["_Actor__register_consumer"])

	def test_init(self):
		#defaults
		manager = AsyncContextManager()
		self.assertEqual(manager._AsyncContextManager__async_class, gevent.event.Event)
		self.assertNotEqual(manager._AsyncContextManager__async_hidden_key, None)
		self.assertEqual(len(manager._AsyncContextManager__async_hidden_key), 32)
		self.assertEqual(isinstance(manager._AsyncContextManager__running, gevent.event.Event), True)
		self.assertEqual(manager._AsyncContextManager__running.is_set(), False)
		self.assertEqual(isinstance(manager._AsyncContextManager__stopped, gevent.event.Event), True)
		self.assertEqual(manager._AsyncContextManager__stopped.is_set(), True)
		self.assertEqual(isinstance(manager._AsyncContextManager__sub_threads, list), True)
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 0)
		self.assertEqual(get_async_manager()._AsyncManager__managers[manager._AsyncContextManager__async_hidden_key], manager)

	def test_del(self):
		def test_func(*args, **kwargs): pass
		self.assertEqual(len(get_async_manager()._AsyncManager__managers), 0)
		manager = AsyncContextManager()
		self.assertEqual(len(get_async_manager()._AsyncManager__managers), 1)
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 0)
		self.assertEqual(len(get_restart_pool().greenlets), 0)
		manager.spawn_thread(run=test_func)
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 1)
		self.assertEqual(len(get_restart_pool().greenlets), 1)
		manager.__del__()
		self.assertEqual(len(get_async_manager()._AsyncManager__managers), 0)
		self.assertEqual(len(get_restart_pool().greenlets), 1)
		sleep();
		self.assertEqual(len(get_restart_pool().greenlets), 0)

	def test_start(self):
		def test_func(*args, **kwargs): pass
		manager = AsyncContextManager()
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 0)
		manager.spawn_thread(run=test_func)
		manager._AsyncContextManager__running.set()
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 1)
		for greenlet in manager._AsyncContextManager__sub_threads:
			self.assertEqual(greenlet.running, True)
		sleep(0)
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 1)
		for greenlet in manager._AsyncContextManager__sub_threads:
			self.assertEqual(greenlet.running, False)
		manager._AsyncContextManager__running.clear()
		manager._AsyncContextManager__stopped.set()
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 1)
		self.assertEqual(manager._AsyncContextManager__running.is_set(), False)
		self.assertEqual(manager._AsyncContextManager__stopped.is_set(), True)
		for greenlet in manager._AsyncContextManager__sub_threads:
			self.assertEqual(greenlet.running, False)
		manager._AsyncContextManager__start()
		self.assertEqual(manager._AsyncContextManager__running.is_set(), True)
		self.assertEqual(manager._AsyncContextManager__stopped.is_set(), False)
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 1)
		for greenlet in manager._AsyncContextManager__sub_threads:
			self.assertEqual(greenlet.running, True)
		manager._AsyncContextManager__stop() #shutdown


		MockAsyncContextManager = funcs_tester(clazz=AsyncContextManager, func_definitions={"_AsyncContextManager__respawn_stopped_greenlets":None})
		manager = MockAsyncContextManager()
		_test_func(self=self, obj=manager, func_name="_AsyncContextManager__respawn_stopped_greenlets", did=False, args=None, kwargs=None, count=0)
		manager._AsyncContextManager__start()
		_test_func(self=self, obj=manager, func_name="_AsyncContextManager__respawn_stopped_greenlets", did=True, args=tuple(), kwargs=dict(), count=1)
		manager._AsyncContextManager__stop() #shutdown

	def test__AsyncContextManager__respawn_stopped_greenlets(self):
		def test_func(*args, **kwargs): pass
		manager = AsyncContextManager()
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 0)
		manager.spawn_thread(run=test_func)
		manager._AsyncContextManager__running.set()
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 1)
		for greenlet in manager._AsyncContextManager__sub_threads:
			self.assertEqual(greenlet.running, True)
		sleep(0)
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 1)
		for greenlet in manager._AsyncContextManager__sub_threads:
			self.assertEqual(greenlet.running, False)
		manager._AsyncContextManager__running.clear()
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 1)
		for greenlet in manager._AsyncContextManager__sub_threads:
			self.assertEqual(greenlet.running, False)
		manager._AsyncContextManager__respawn_stopped_greenlets()
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 1)
		for greenlet in manager._AsyncContextManager__sub_threads:
			self.assertEqual(greenlet.running, True)

	def test__AsyncContextManager__kill_running_greenlets(self):
		streamer = RedirectStdStreams()
		def test_func(*args, **kwargs):
			with streamer:
				sleep(); print "1234"
		manager = AsyncContextManager()
		self.assertEqual(str(streamer.stdout), "")
		self.assertEqual(len(get_restart_pool().greenlets), 0)
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 0)
		manager.spawn_thread(run=test_func, graceful_restart=False)
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 1)
		self.assertEqual(len(get_restart_pool().greenlets), 1)
		manager._AsyncContextManager__running.set()
		sleep(); sleep()
		self.assertEqual(str(streamer.stdout), "1234\n")
		self.assertEqual(len(get_restart_pool().greenlets), 0)
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 0)
		streamer.stdout = ""
		self.assertEqual(str(streamer.stdout), "")
		manager.spawn_thread(run=test_func, graceful_restart=False)
		self.assertEqual(len(get_restart_pool().greenlets), 1)
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 1)
		manager._AsyncContextManager__kill_running_greenlets()
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 1)
		self.assertEqual(len(get_restart_pool().greenlets), 1)
		sleep()
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 1)
		self.assertEqual(len(get_restart_pool().greenlets), 0)
		self.assertEqual(str(streamer.stdout), "")

	def test_stop(self):
		MockAsyncContextManager = funcs_tester(clazz=AsyncContextManager, func_definitions={"_AsyncContextManager__kill_running_greenlets":None})
		manager = MockAsyncContextManager()
		manager._AsyncContextManager__running.set()
		_test_func(self=self, obj=manager, func_name="_AsyncContextManager__kill_running_greenlets", did=False, args=None, kwargs=None, count=0)
		self.assertEqual(manager._AsyncContextManager__running.is_set(), True)
		manager._AsyncContextManager__stop()
		self.assertEqual(manager._AsyncContextManager__running.is_set(), False)
		_test_func(self=self, obj=manager, func_name="_AsyncContextManager__kill_running_greenlets", did=True, args=tuple(), kwargs=dict(), count=1)

	def test_context_management(self):
		def test_func(*args, **kwargs): sleep(); pass
		manager = AsyncContextManager()
		manager.spawn_thread(run=test_func, graceful_restart=False)
		manager.spawn_thread(run=test_func)
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 2)
		with manager:
			self.assertEqual(len(manager._AsyncContextManager__sub_threads), 2)
			self.assertEqual(len(get_restart_pool().greenlets), 2)
			for greenlet in manager._AsyncContextManager__sub_threads:
				self.assertEqual(greenlet.running, True)
			sleep(); sleep()
			self.assertEqual(len(manager._AsyncContextManager__sub_threads), 1)
			self.assertEqual(len(get_restart_pool().greenlets), 1)
			self.assertEqual(manager._AsyncContextManager__sub_threads[0].running, True)
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 0)
		self.assertEqual(len(get_restart_pool().greenlets), 0)

	def test_spawn_thread(self):
		def test_func(*args, **kwargs): pass
		MockAsyncContextManager = funcs_tester(clazz=AsyncContextManager, func_definitions={"_AsyncContextManager__force_running": None})
		manager = MockAsyncContextManager()
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 0)
		self.assertEqual(len(get_restart_pool().greenlets), 0)
		_test_func(self=self, obj=manager, func_name="_AsyncContextManager__force_running", did=False, args=None, kwargs=None, count=0)
		greenlet1 = manager.spawn_thread(run=test_func)
		_test_func(self=self, obj=manager, func_name="_AsyncContextManager__force_running", did=False, args=None, kwargs=None, count=0)
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 1)
		self.assertEqual(len(get_restart_pool().greenlets), 1)
		self.assertEqual(greenlet1.rg_parent, manager)
		self.assertEqual(greenlet1._run, manager._AsyncContextManager__force_running)
		manager._AsyncContextManager__start()
		sleep(0)
		_test_func(self=self, obj=manager, func_name="_AsyncContextManager__force_running", did=True, args=tuple(), kwargs={"forced_func":test_func}, count=1)
		manager._AsyncContextManager__stop() #shutdown

	def test__AsyncContextManager__force_running(self):
		MockAsyncContextManager = funcs_tester(clazz=AsyncContextManager, func_definitions={"rando": None})
		manager = MockAsyncContextManager()
		manager.spawn_thread(run=manager.rando, graceful_restart=False)
		_test_func(self=self, obj=manager, func_name="rando", did=False, args=None, kwargs=None, count=0)
		sleep(0)
		_test_func(self=self, obj=manager, func_name="rando", did=False, args=None, kwargs=None, count=0)
		manager._AsyncContextManager__running.set()
		_test_func(self=self, obj=manager, func_name="rando", did=False, args=None, kwargs=None, count=0)
		sleep(0)
		_test_func(self=self, obj=manager, func_name="rando", did=True, args=tuple(), kwargs=dict(), count=1)
		manager._AsyncContextManager__stop() #shutdown

	def test_is_running(self):
		manager = AsyncContextManager()
		self.assertEqual(manager._AsyncContextManager__running.is_set(), False)
		self.assertEqual(manager._AsyncContextManager__running.is_set(), manager.is_running())
		manager._AsyncContextManager__running.set()
		self.assertEqual(manager._AsyncContextManager__running.is_set(), True)
		self.assertEqual(manager._AsyncContextManager__running.is_set(), manager.is_running())
		manager._AsyncContextManager__stop() #shutdown

	def test_wait_for_running(self):
		manager = AsyncContextManager()
		self.assertEqual(len(get_restart_pool().greenlets), 0)
		get_restart_pool().spawn(run=manager.wait_for_running, graceful_restart=False)
		self.assertEqual(len(get_restart_pool().greenlets), 1)
		sleep()
		self.assertEqual(len(get_restart_pool().greenlets), 1)
		manager._AsyncContextManager__running.set()
		self.assertEqual(len(get_restart_pool().greenlets), 1)
		sleep();
		self.assertEqual(len(get_restart_pool().greenlets), 0)
		manager._AsyncContextManager__running.clear() #shutdown

	def test_wait_for_stop(self):
		manager = AsyncContextManager()
		manager._AsyncContextManager__stopped.clear()
		self.assertEqual(len(get_restart_pool().greenlets), 0)
		get_restart_pool().spawn(run=manager.wait_for_stop, graceful_restart=False)
		self.assertEqual(len(get_restart_pool().greenlets), 1)
		sleep()
		self.assertEqual(len(get_restart_pool().greenlets), 1)
		manager._AsyncContextManager__stopped.set()
		self.assertEqual(len(get_restart_pool().greenlets), 1)
		sleep();
		self.assertEqual(len(get_restart_pool().greenlets), 0)

	def test_trigger_stop(self):
		manager = AsyncContextManager()
		manager._AsyncContextManager__stopped.clear()
		self.assertEqual(manager._AsyncContextManager__stopped.is_set(), False)
		manager.trigger_stop()
		self.assertEqual(manager._AsyncContextManager__stopped.is_set(), True)

	def test_swap_thread(self):
		class Rando: pass
		rando1, rando2, rando3 = Rando(), Rando(), Rando()
		manager = AsyncContextManager()
		manager._AsyncContextManager__sub_threads.append(rando1)
		manager._AsyncContextManager__sub_threads.append(rando2)
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 2)
		self.assertEqual(rando1 in manager._AsyncContextManager__sub_threads, True)
		self.assertEqual(rando2 in manager._AsyncContextManager__sub_threads, True)
		self.assertEqual(rando3 in manager._AsyncContextManager__sub_threads, False)
		manager.swap_thread(old_thread=rando1, new_thread=rando3)
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 2)
		self.assertEqual(rando1 in manager._AsyncContextManager__sub_threads, False)
		self.assertEqual(rando2 in manager._AsyncContextManager__sub_threads, True)
		self.assertEqual(rando3 in manager._AsyncContextManager__sub_threads, True)
		manager.swap_thread(old_thread=rando1, new_thread=rando3)
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 2)
		self.assertEqual(rando1 in manager._AsyncContextManager__sub_threads, False)
		self.assertEqual(rando2 in manager._AsyncContextManager__sub_threads, True)
		self.assertEqual(rando3 in manager._AsyncContextManager__sub_threads, True)

	def test_pop_thread(self):
		class Rando: pass
		rando1, rando2, rando3 = Rando(), Rando(), Rando()
		manager = AsyncContextManager()
		manager._AsyncContextManager__sub_threads.append(rando1)
		manager._AsyncContextManager__sub_threads.append(rando2)
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 2)
		self.assertEqual(rando1 in manager._AsyncContextManager__sub_threads, True)
		self.assertEqual(rando2 in manager._AsyncContextManager__sub_threads, True)
		self.assertEqual(rando3 in manager._AsyncContextManager__sub_threads, False)
		manager.pop_thread(old_thread=rando1)
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 1)
		self.assertEqual(rando1 in manager._AsyncContextManager__sub_threads, False)
		self.assertEqual(rando2 in manager._AsyncContextManager__sub_threads, True)
		self.assertEqual(rando3 in manager._AsyncContextManager__sub_threads, False)
		manager.pop_thread(old_thread=rando3)
		self.assertEqual(len(manager._AsyncContextManager__sub_threads), 1)
		self.assertEqual(rando1 in manager._AsyncContextManager__sub_threads, False)
		self.assertEqual(rando2 in manager._AsyncContextManager__sub_threads, True)
		self.assertEqual(rando3 in manager._AsyncContextManager__sub_threads, False)

	def test_me(self):
		def test_func(*args, **kwargs): pass
		class loop(gevent.corecext.loop): 
			def run_callback(self, func, *args):
				print "appending"
		
		print gevent.corecext.loop
		gevent.corecext.loop = loop
		print gevent.corecext.loop
		get_restart_pool().kill()
		greenlet1 = get_restart_pool().spawn(run=test_func)

		'''
		def test_func(*args, **kwargs): gevent.sleep(); gevent.sleep(); pass
		greenlet1 = get_restart_pool().spawn(run=test_func)
		greenlet2 = get_restart_pool().spawn(run=test_func)
		print "PRE:    ",greenlet1.parent.loop._callbacks
		gevent.sleep()
		greenlet1.kill()
		print "POST:   ",greenlet1.parent.loop._callbacks
		gevent.sleep()
		print "POST:   ",greenlet1.parent.loop._callbacks
		'''


		