

import signal
from pypes.util.async import AsyncManager, AsyncContextManager, RestartableGreenlet, KilledException, sleep, RestartPool, timestamp
from pypes.globals.async import get_restart_pool, DEFAULT_SLEEP_INTERVAL, get_async_manager, _override_async_manager, _override_restart_pool
from pypes.testutils import funcs_tester, _test_func, BaseUnitTest, _test_meta_func_error
from pypes.util import RedirectStdStreams
import gevent
import os
from pypes.metas.async import IgnoreDerivativesMeta
from gevent.hub import LoopExit
# import LoopExit

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

	def test_interupt_signal(self):
		_override_async_manager(manager=AsyncManager())
		assert get_async_manager().stopped
		assert not get_async_manager().running
		with get_async_manager():
			assert not get_async_manager().stopped
			assert get_async_manager().running
			os.kill(os.getpid(), signal.SIGINT); sleep()
			assert get_async_manager().stopped
			assert not get_async_manager().running

	def test_termination_signal(self):
		_override_async_manager(manager=AsyncManager())
		assert get_async_manager().stopped
		assert not get_async_manager().running
		with get_async_manager():
			assert not get_async_manager().stopped
			assert get_async_manager().running
			os.kill(os.getpid(), signal.SIGTERM); sleep()
			assert get_async_manager().stopped
			assert not get_async_manager().running

	def test_init(self):
		assert isinstance(get_async_manager()._AsyncManager__managers, dict)
		assert len(get_async_manager()._AsyncManager__managers) == 0
		assert get_async_manager().stopped
		assert not get_async_manager().running

	def test_create_context_manager_1(self):
		#test success while stopped
		_override_async_manager(manager=AsyncManager())
		assert len(get_async_manager()._AsyncManager__managers) == 0
		assert get_async_manager().stopped
		manager = AsyncContextManager()
		assert len(get_async_manager()._AsyncManager__managers) == 1
		assert get_async_manager().stopped
		assert get_async_manager()._AsyncManager__managers.values()[0] == manager
		assert manager.stopped

	def test_create_context_manager_2(self):
		#test success while running
		_override_async_manager(manager=AsyncManager())
		assert len(get_async_manager()._AsyncManager__managers) == 0
		assert get_async_manager().stopped
		with get_async_manager():
			assert get_async_manager().running
			assert len(get_async_manager()._AsyncManager__managers) == 0
			manager = AsyncContextManager()
			assert len(get_async_manager()._AsyncManager__managers) == 1
			assert get_async_manager().running
			assert get_async_manager()._AsyncManager__managers.values()[0] == manager
			assert manager.stopped
			sleep(0)
			assert manager.running
			get_async_manager().trigger_stop()

	def test_remove_context_manager_1(self):
		#test success while stopped
		_override_async_manager(manager=AsyncManager())
		assert get_async_manager().stopped
		assert len(get_async_manager()) == 0
		manager = AsyncContextManager(async_hidden_key="1")
		assert get_async_manager().stopped
		assert len(get_async_manager()) == 1
		get_async_manager().remove_context_manager(key="1")
		assert len(get_async_manager()) == 0
		assert get_async_manager().stopped

	def test_remove_context_manager_2(self):
		#test success while running
		_override_async_manager(manager=AsyncManager())
		assert get_async_manager().stopped
		assert len(get_async_manager()) == 0
		manager = AsyncContextManager(async_hidden_key="1")
		assert len(get_async_manager()) == 1
		assert get_async_manager().stopped
		assert manager.stopped
		with get_async_manager():
			assert get_async_manager().running
			assert not manager.running
			sleep(0)
			assert manager.running
			get_async_manager().remove_context_manager(key="1")
			assert len(get_async_manager()) == 0
			assert get_async_manager().running
			assert manager.stopped
			get_async_manager().trigger_stop()

	def test_remove_context_manager_3(self):
		#test missing key while stopped
		_override_async_manager(manager=AsyncManager())
		assert get_async_manager().stopped
		assert len(get_async_manager()) == 0
		manager = AsyncContextManager(async_hidden_key="1")
		assert get_async_manager().stopped
		assert len(get_async_manager()) == 1
		get_async_manager().remove_context_manager(key="2")
		assert len(get_async_manager()) == 1
		assert get_async_manager().stopped
	
	def test_remove_context_manager_4(self):
		#test missing key while running
		_override_async_manager(manager=AsyncManager())
		assert get_async_manager().stopped
		assert len(get_async_manager()) == 0
		manager = AsyncContextManager(async_hidden_key="1")
		assert len(get_async_manager()) == 1
		assert get_async_manager().stopped
		assert manager.stopped
		with get_async_manager():
			assert get_async_manager().running
			assert not manager.running
			sleep(0)
			assert manager.running
			get_async_manager().remove_context_manager(key="2")
			assert len(get_async_manager()) == 1
			assert get_async_manager().running
			assert manager.running
			get_async_manager().trigger_stop()

	def test_wait_for_stop(self):
		def some_func():
			sleep(.05)
			get_async_manager().trigger_stop()
		get_restart_pool().spawn(run=some_func, greenlet_manager=AsyncContextManager(), graceful_restart=False, rough_restart=False)
		start = timestamp()
		with get_async_manager():
			get_async_manager().wait_for_stop()
		end = timestamp()
		dif = end - start
		assert dif > 0.04 and dif < 0.06

	def test_context_manager(self):
		#expected usage
		_override_async_manager(manager=AsyncManager())
		assert len(get_async_manager()) == 0
		assert len(get_restart_pool().greenlets) == 0
		AsyncContextManager(async_hidden_key="1"); AsyncContextManager(async_hidden_key="2"); AsyncContextManager(async_hidden_key="3")
		assert len(get_restart_pool().greenlets) == 0
		assert len(get_async_manager()) == 3
		for key, manager in get_async_manager():
			assert manager.stopped
		with get_async_manager():
			assert len(get_restart_pool().greenlets) == 3
			for key, manager in get_async_manager():
				assert manager.stopped
			sleep() #allows managers to start  # typically would be a block here
			assert len(get_restart_pool().greenlets) == 3
			for key, manager in get_async_manager():
				assert manager.running
			get_async_manager().trigger_stop()
		assert len(get_restart_pool().greenlets) == 0
		for key, manager in get_async_manager():
			assert manager.stopped

		#restartablity
		assert len(get_restart_pool().greenlets) == 0
		assert len(get_async_manager()) == 3
		for key, manager in get_async_manager():
			assert manager.stopped
		with get_async_manager():
			assert len(get_restart_pool().greenlets) == 3
			for key, manager in get_async_manager():
				assert manager.stopped
			sleep() #allows managers to start  # typically would be a block here
			assert len(get_restart_pool().greenlets) == 3
			for key, manager in get_async_manager():
				assert manager.running
			get_async_manager().trigger_stop()
		assert len(get_restart_pool().greenlets) == 0
		for key, manager in get_async_manager():
			assert manager.stopped

		#infinite loop
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
		manager = AsyncContextManager()

		with self.assertRaises(TypeError):
			RestartableGreenlet(run=run_test)

		with self.assertRaises(TypeError):
			RestartableGreenlet(greenlet_manager=manager)

		#defaults
		greenlet = RestartableGreenlet(run=run_test, greenlet_manager=manager)
		assert isinstance(greenlet, RestartableGreenlet)
		assert greenlet.manager == manager
		assert greenlet.graceful_restart
		assert greenlet.rough_restart
		assert greenlet.logger is None
		assert greenlet.rg_args == tuple()
		assert greenlet.rg_kwargs == dict()
		assert not greenlet.killed
		assert not greenlet.running

		#inits
		logger = Logger()
		greenlet = RestartableGreenlet(run=run_test, greenlet_manager=manager, graceful_restart=False, rough_restart=False, logger=logger, other="test", killed=True)
		assert isinstance(greenlet, RestartableGreenlet)
		assert greenlet.manager == manager
		assert not greenlet.graceful_restart
		assert not greenlet.rough_restart
		assert greenlet.logger == logger
		assert greenlet.rg_args == tuple()
		assert greenlet.rg_kwargs == {"other": "test", "killed": True}
		assert not greenlet.killed

	def test_state(self):
		streamer = RedirectStdStreams()
		class MockRestartableGreenlet(funcs_tester(clazz=RestartableGreenlet)):
			def _report_error(self, *args, **kwargs):
				with streamer:
					super(MockRestartableGreenlet, self)._report_error(*args, **kwargs)
		def run_func_graceful(): pass
		def run_func_rough(): print "11233"; raise Exception("????")
		def run_func_kill(): raise KilledException
		class MockPool(gevent.pool.Pool):
			def kill(self, greenlets=None, *args, **kwargs):
				super(MockPool, self).kill(*args, **kwargs)
		manager = AsyncContextManager()

		#test graceful stop with graceful restart
		_override_restart_pool(pool=MockPool(greenlet_class=MockRestartableGreenlet))
		greenlet = get_restart_pool().spawn(run=run_func_graceful, greenlet_manager=manager)
		assert greenlet.running and not greenlet.stopped and not greenlet.stopped_rough and not greenlet.stopped_graceful
		assert not greenlet.rough_restartable and not greenlet.graceful_restartable and not greenlet.restartable
		sleep(0)
		assert not greenlet.running and greenlet.stopped and not greenlet.stopped_rough and greenlet.stopped_graceful
		assert not greenlet.rough_restartable and not greenlet.graceful_restartable and not greenlet.restartable
		greenlet = get_restart_pool().spawn(run=run_func_graceful, greenlet_manager=manager)
		with manager:
			assert greenlet.running and not greenlet.stopped and not greenlet.stopped_rough and not greenlet.stopped_graceful
			assert not greenlet.rough_restartable and not greenlet.graceful_restartable and not greenlet.restartable
			sleep(0)
			assert not greenlet.running and greenlet.stopped and not greenlet.stopped_rough and greenlet.stopped_graceful
			assert not greenlet.rough_restartable and greenlet.graceful_restartable and greenlet.restartable
			manager.trigger_stop()

		#test graceful stop without graceful restart
		greenlet = get_restart_pool().spawn(run=run_func_graceful, greenlet_manager=manager, graceful_restart=False)
		assert greenlet.running and not greenlet.stopped and not greenlet.stopped_rough and not greenlet.stopped_graceful
		assert not greenlet.rough_restartable and not greenlet.graceful_restartable and not greenlet.restartable
		sleep(0)
		assert not greenlet.running and greenlet.stopped and not greenlet.stopped_rough and greenlet.stopped_graceful
		assert not greenlet.rough_restartable and not greenlet.graceful_restartable and not greenlet.restartable
		greenlet = get_restart_pool().spawn(run=run_func_graceful, greenlet_manager=manager, graceful_restart=False)
		with manager:
			assert greenlet.running and not greenlet.stopped and not greenlet.stopped_rough and not greenlet.stopped_graceful
			assert not greenlet.rough_restartable and not greenlet.graceful_restartable and not greenlet.restartable
			sleep(0)
			assert not greenlet.running and greenlet.stopped and not greenlet.stopped_rough and greenlet.stopped_graceful
			assert not greenlet.rough_restartable and not greenlet.graceful_restartable and not greenlet.restartable
			manager.trigger_stop()

		#test rough stop with rough restart
		greenlet = get_restart_pool().spawn(run=run_func_rough, greenlet_manager=manager)
		assert greenlet.running and not greenlet.stopped and not greenlet.stopped_rough and not greenlet.stopped_graceful
		assert not greenlet.rough_restartable and not greenlet.graceful_restartable and not greenlet.restartable
		sleep(0)
		assert not greenlet.running and greenlet.stopped and greenlet.stopped_rough and not greenlet.stopped_graceful
		assert not greenlet.rough_restartable and not greenlet.graceful_restartable and not greenlet.restartable
		greenlet = get_restart_pool().spawn(run=run_func_rough, greenlet_manager=manager)
		with manager:
			assert greenlet.running and not greenlet.stopped and not greenlet.stopped_rough and not greenlet.stopped_graceful
			assert not greenlet.rough_restartable and not greenlet.graceful_restartable and not greenlet.restartable
			sleep(0)
			assert not greenlet.running and greenlet.stopped and greenlet.stopped_rough and not greenlet.stopped_graceful
			assert greenlet.rough_restartable and not greenlet.graceful_restartable and greenlet.restartable
			manager.trigger_stop()

		#test rough stop without rough restart
		greenlet = get_restart_pool().spawn(run=run_func_rough, greenlet_manager=manager, rough_restart=False)
		assert greenlet.running and not greenlet.stopped and not greenlet.stopped_rough and not greenlet.stopped_graceful
		assert not greenlet.rough_restartable and not greenlet.graceful_restartable and not greenlet.restartable
		sleep(0)
		assert not greenlet.running and greenlet.stopped and greenlet.stopped_rough and not greenlet.stopped_graceful
		assert not greenlet.rough_restartable and not greenlet.graceful_restartable and not greenlet.restartable
		greenlet = get_restart_pool().spawn(run=run_func_rough, greenlet_manager=manager, rough_restart=False)
		with manager:
			assert greenlet.running and not greenlet.stopped and not greenlet.stopped_rough and not greenlet.stopped_graceful
			assert not greenlet.rough_restartable and not greenlet.graceful_restartable and not greenlet.restartable
			sleep(0)
			assert not greenlet.running and greenlet.stopped and greenlet.stopped_rough and not greenlet.stopped_graceful
			assert not greenlet.rough_restartable and not greenlet.graceful_restartable and not greenlet.restartable
			manager.trigger_stop()

		#test killed
		greenlet = get_restart_pool().spawn(run=run_func_kill, greenlet_manager=manager)
		assert greenlet.running and not greenlet.stopped and not greenlet.stopped_rough and not greenlet.stopped_graceful
		assert not greenlet.rough_restartable and not greenlet.graceful_restartable and not greenlet.restartable
		sleep(0)
		assert not greenlet.running and greenlet.stopped and greenlet.stopped_rough and not greenlet.stopped_graceful
		assert not greenlet.rough_restartable and not greenlet.graceful_restartable and not greenlet.restartable
		greenlet = get_restart_pool().spawn(run=run_func_kill, greenlet_manager=manager)
		with manager:
			assert greenlet.running and not greenlet.stopped and not greenlet.stopped_rough and not greenlet.stopped_graceful
			assert not greenlet.rough_restartable and not greenlet.graceful_restartable and not greenlet.restartable
			sleep(0)
			assert not greenlet.running and greenlet.stopped and greenlet.stopped_rough and not greenlet.stopped_graceful
			assert not greenlet.rough_restartable and not greenlet.graceful_restartable and not greenlet.restartable
			manager.trigger_stop()
		

	def test__report_error(self):
		def run_test(): pass
		_override_restart_pool(pool=gevent.pool.Pool(greenlet_class=RestartableGreenlet))
		greenlet = get_restart_pool().spawn(run=run_test, greenlet_manager=AsyncContextManager())
		streamer = RedirectStdStreams() 
		with streamer:
			greenlet._report_error(exc_info=[KilledException, KilledException(), 0])
		assert len(streamer.stderr) == 0
		with streamer:
			greenlet._report_error(exc_info=[Exception, Exception(), 0])
		assert len(streamer.stderr) != 0

	def test_kill(self):
		_override_restart_pool(pool=gevent.pool.Pool(greenlet_class=RestartableGreenlet))
		def callback(greenlet): self.assertEqual(isinstance(greenlet.exception, BreakoutException), True)
		def run_test(*args, **kwargs): sleep()
		assert len(get_restart_pool().greenlets) == 0
		greenlet = get_restart_pool().spawn(run=run_test, greenlet_manager=AsyncContextManager())
		assert len(get_restart_pool().greenlets) == 1
		greenlet.link_exception(callback=callback)
		sleep()
		assert len(get_restart_pool().greenlets) == 1
		greenlet.kill()
		assert len(get_restart_pool().greenlets) == 0


class TestRestartPool(BaseUnitTest):

	def test_meta(self):
		with self.assertRaises(TypeError):
			class Deriv(RestartPool):
				pass

	def test_init(self):
		#defaults
		_override_restart_pool(pool=RestartPool())
		pool = RestartPool()
		assert get_restart_pool().restart_sleep_interval == DEFAULT_SLEEP_INTERVAL
		assert get_restart_pool().graceful_restart
		assert get_restart_pool().rough_restart
		assert get_restart_pool().logger is None
		assert get_restart_pool().greenlet_class == RestartableGreenlet

		#overrides
		_override_restart_pool(pool=RestartPool(restart_sleep_interval=2, graceful_restart=False, rough_restart=False, logger=7, greenlet_class=gevent.greenlet.Greenlet))
		assert get_restart_pool().restart_sleep_interval == 2
		assert not get_restart_pool().graceful_restart
		assert not get_restart_pool().rough_restart
		assert get_restart_pool().logger == 7
		assert get_restart_pool().greenlet_class == RestartableGreenlet

	def test_spawn(self):
		def test_func(*args, **kwargs): pass
		manager = AsyncContextManager()

		with self.assertRaises(TypeError):
			get_restart_pool().spawn(run=test_func)
		with self.assertRaises(TypeError):
			get_restart_pool().spawn(greenlet_manager=manager)

		#instance
		_override_restart_pool(pool=RestartPool())
		greenlet = get_restart_pool().spawn(run=test_func, greenlet_manager=manager)
		assert isinstance(greenlet, RestartableGreenlet)

		_override_restart_pool(pool=RestartPool(greenlet_class=gevent.greenlet.Greenlet))
		greenlet = get_restart_pool().spawn(run=test_func, greenlet_manager=manager)
		assert isinstance(greenlet, RestartableGreenlet)

		#defaults
		_override_restart_pool(pool=RestartPool())
		greenlet = get_restart_pool().spawn(run=test_func, greenlet_manager=manager)
		assert greenlet.manager == manager
		assert greenlet.graceful_restart
		assert greenlet.rough_restart
		assert greenlet.logger is None

		_override_restart_pool(pool=RestartPool(graceful_restart=False, rough_restart=False, logger=7))
		greenlet = get_restart_pool().spawn(run=test_func, greenlet_manager=manager)
		assert greenlet.manager == manager
		assert not greenlet.graceful_restart
		assert not greenlet.rough_restart
		assert greenlet.logger == 7

		#overrides
		_override_restart_pool(pool=RestartPool())
		greenlet = get_restart_pool().spawn(run=test_func, greenlet_manager=manager, graceful_restart=False, rough_restart=False, logger=7)
		assert greenlet.manager == manager
		assert not greenlet.graceful_restart
		assert not greenlet.rough_restart
		assert greenlet.logger == 7

		_override_restart_pool(pool=RestartPool(graceful_restart=False, rough_restart=False, logger=7))
		greenlet = get_restart_pool().spawn(run=test_func, greenlet_manager=manager, graceful_restart=True, rough_restart=True, logger=8)
		assert greenlet.manager == manager
		assert greenlet.graceful_restart
		assert greenlet.rough_restart
		assert greenlet.logger == 8

		#test links
		_override_restart_pool(pool=RestartPool())
		greenlet = get_restart_pool().spawn(run=test_func, greenlet_manager=manager, graceful_restart=False, rough_restart=False, logger=7)
		assert len(greenlet._links) == 3  #default, graceful, and irregular links


	def test_graceful_restart(self):
		def test_func(): pass
		manager = AsyncContextManager()
		with manager:

			#graceful_restart = True
			_override_restart_pool(pool=RestartPool())
			assert len(get_restart_pool().greenlets) == 0
			greenlet = get_restart_pool().spawn(run=test_func, graceful_restart=True, greenlet_manager=manager)
			assert len(get_restart_pool().greenlets) == 1
			assert list(get_restart_pool().greenlets)[0] == greenlet
			sleep(0); sleep(0); sleep()
			assert len(get_restart_pool().greenlets) == 1
			assert list(get_restart_pool().greenlets)[0] != greenlet

			#graceful_restart = False
			_override_restart_pool(pool=RestartPool())
			assert len(get_restart_pool().greenlets) == 0
			greenlet = get_restart_pool().spawn(run=test_func, graceful_restart=False, greenlet_manager=manager)
			assert len(get_restart_pool().greenlets) == 1
			sleep(0); sleep(0)
			assert len(get_restart_pool().greenlets) == 0

	def test_rough_restart(self):
		def test_func(): raise Exception()
		manager = AsyncContextManager()

		with manager:
			#rough_restart = True
			_override_restart_pool(pool=RestartPool())
			assert len(get_restart_pool().greenlets) == 0
			greenlet = get_restart_pool().spawn(run=test_func, rough_restart=True, greenlet_manager=manager)
			assert len(get_restart_pool().greenlets) == 1
			assert list(get_restart_pool().greenlets)[0] == greenlet
			sleep(0); sleep(0); sleep()
			assert len(get_restart_pool().greenlets) == 1
			assert list(get_restart_pool().greenlets)[0] != greenlet

			#rough_restart = False
			_override_restart_pool(pool=RestartPool())
			assert len(get_restart_pool().greenlets) == 0
			greenlet = get_restart_pool().spawn(run=test_func, rough_restart=False, greenlet_manager=manager)
			assert len(get_restart_pool().greenlets) == 1
			sleep(0); sleep(0)
			assert len(get_restart_pool().greenlets) == 0

	def test_kill(self):
		def test_func_1(): pass
		def test_func_2(): sleep()
		manager = AsyncContextManager()
		with manager:
			#killed with sleep
			_override_restart_pool(pool=RestartPool())
			assert len(get_restart_pool().greenlets) == 0
			greenlet = get_restart_pool().spawn(run=test_func_1, graceful_restart=True, rough_restart=True, greenlet_manager=manager)
			assert len(get_restart_pool().greenlets) == 1
			get_restart_pool().kill()
			assert len(get_restart_pool().greenlets) == 0

			#killed without sleep
			_override_restart_pool(pool=RestartPool())
			assert len(get_restart_pool().greenlets) == 0
			greenlet = get_restart_pool().spawn(run=test_func_2, graceful_restart=True, rough_restart=True, greenlet_manager=manager)
			assert len(get_restart_pool().greenlets) == 1
			get_restart_pool().kill()
			assert len(get_restart_pool().greenlets) == 0

			#kill multiple
			_override_restart_pool(pool=RestartPool())
			assert len(get_restart_pool().greenlets) == 0
			greenlet = get_restart_pool().spawn(run=test_func_1, graceful_restart=True, rough_restart=True, greenlet_manager=manager)
			greenlet = get_restart_pool().spawn(run=test_func_1, graceful_restart=True, rough_restart=True, greenlet_manager=manager)
			assert len(get_restart_pool().greenlets) == 2
			get_restart_pool().kill()
			assert len(get_restart_pool().greenlets) == 0

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


		