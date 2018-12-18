from pypes.actor import Actor
from pypes.event import Event, HttpEvent, JSONEvent, XMLEvent
from pypes.globals.async import get_restart_pool, get_async_manager
from pypes.util.queue import QueuePool, Queue
from pypes.testutils import funcs_tester, _test_func
from pypes.util import remove_dupes, raise_exception_func
from pypes.util.logger import Logger
from pypes.util.errors import (QueueConnected, InvalidActorOutput, QueueEmpty, InvalidEventConversion, InvalidActorInput, QueueFull, PypesException)
from pypes.util.async import sleep
import abc
import gevent
import time
import unittest

class MockActor(Actor):
	def consume(self, *args, **kwargs):
		pass
MockedActor = None

class TestActor(unittest.TestCase):

	def setUp(self):
		get_restart_pool().kill()
		global MockedActor
		MockedActor = funcs_tester(clazz=MockActor)

	def tearDown(self):
		get_restart_pool().kill()
		global MockedActor
		MockedActor = None

	def _test_meta_func_error(self, root_clazz=object, func_names=[], *args, **kwargs):
		attrs_dict = {func_name:lambda x: x for func_name in func_names}
		with self.assertRaises(TypeError):
			BadActor = type('BadActor', (root_clazz, object), attrs_dict)

	def _test_pool(self, actor, error, inbound, outbound, logs):
		self.assertEqual(len(actor.pool.error), error)
		self.assertEqual(len(actor.pool.inbound), inbound)
		self.assertEqual(len(actor.pool.outbound), outbound)
		self.assertEqual(len(actor.pool.logs), logs)

	def _test_queue(self, 
		post_src_err=0, post_src_in=0, post_src_out=0, post_src_log=1,
		post_dest_err=0, post_dest_in=0, post_dest_out=0, post_dest_log=1,
		source_queue_name=None, destination_queue_name=None, pool_scope_name=None, check_exists=None, destination=None,
		test_inbox_name="", test_src_pool_name="", test_outbox_name="", test_dest_pool_name="",
		func_name=""
		):

		source_actor, destination_actor, kwargs = MockActor(name='source_name'), MockActor(name='destination_name'), {}
		kwargs.update({"destination": destination_actor})
		kwargs.update({"source_queue_name":value for value in [source_queue_name] if not value is None})
		kwargs.update({"destination_queue_name":value for value in [destination_queue_name] if not value is None})
		kwargs.update({"pool_scope":getattr(source_actor.pool, value) for value in [pool_scope_name] if not value is None})
		kwargs.update({"check_exists":value for value in [check_exists] if not value is None})
		kwargs.update({"destination":value for value in [destination] if not value is None})
		kwargs.update({"source_queue_name":value for value in [source_queue_name] if not value is None})

		self._test_pool(actor=source_actor, error=0, inbound=0, outbound=0, logs=1)
		self._test_pool(actor=destination_actor, error=0, inbound=0, outbound=0, logs=1)
		self.assertNotEqual(source_actor.pool.logs.get(source_actor.pool.logs.placeholder, None), None)
		self.assertNotEqual(destination_actor.pool.logs.get(destination_actor.pool.logs.placeholder, None), None)
		getattr(source_actor, func_name)(**kwargs)
		self._test_pool(actor=source_actor, error=post_src_err, inbound=post_src_in, outbound=post_src_out, logs=post_src_log)
		self._test_pool(actor=destination_actor, error=post_dest_err, inbound=post_dest_in, outbound=post_dest_out, logs=post_dest_log)
		self.assertEqual(getattr(source_actor.pool, test_src_pool_name).get(test_outbox_name), 
			getattr(destination_actor.pool, test_dest_pool_name).get(test_inbox_name))
		self.assertIsInstance(getattr(source_actor.pool, test_src_pool_name).get(test_outbox_name), Queue)

	#################
	# __metaclass__ #
	#################

	def test_meta(self):
		#baseline
		GoodActor = type('GoodActor', (Actor, object), {"consume":lambda x: x})
		GoodActor = type('GoodActor', (GoodActor, object), {"input":HttpEvent})
		GoodActor = type('GoodActor', (GoodActor, object), {"output":HttpEvent})

		self._test_meta_func_error(root_clazz=Actor) #missing consume
		#func override tests
		self._test_meta_func_error(root_clazz=GoodActor, func_names=["_Actor__connect_queue"]) 
		self._test_meta_func_error(root_clazz=GoodActor, func_names=["_Actor__register_consumer"])
		self._test_meta_func_error(root_clazz=GoodActor, func_names=["_Actor__loop_send"])
		self._test_meta_func_error(root_clazz=GoodActor, func_names=["_Actor__generate_split_id"])
		self._test_meta_func_error(root_clazz=GoodActor, func_names=["_Actor__try_spawn_consume"])
		self._test_meta_func_error(root_clazz=GoodActor, func_names=["_Actor__consumer"])
		self._test_meta_func_error(root_clazz=GoodActor, func_names=["_Actor__consume_pre_processing"])
		self._test_meta_func_error(root_clazz=GoodActor, func_names=["_Actor__consume_post_processing"])
		self._test_meta_func_error(root_clazz=GoodActor, func_names=["_Actor__consume_wrapper"])
		self._test_meta_func_error(root_clazz=GoodActor, func_names=["_Actor__do_consume"])
		self._test_meta_func_error(root_clazz=GoodActor, func_names=["_Actor__send_event"])
		self._test_meta_func_error(root_clazz=GoodActor, func_names=["_Actor__send_error"])
		self._test_meta_func_error(root_clazz=GoodActor, func_names=["create_event"])
		self._test_meta_func_error(root_clazz=GoodActor, func_names=["connect_error_queue"])
		self._test_meta_func_error(root_clazz=GoodActor, func_names=["connect_queue"])
		self._test_meta_func_error(root_clazz=GoodActor, func_names=["start"])
		self._test_meta_func_error(root_clazz=GoodActor, func_names=["stop"])

		#test I/O vars
		with self.assertRaises(TypeError):
			BadActor = type('BadActor', (Actor, object), {"input": "test"})
		with self.assertRaises(TypeError):
			BadActor = type('BadActor', (Actor, object), {"output": "test"})

	############
	# __init__ #
	############

	def test_init(self):
		with self.assertRaises(TypeError):
			Actor()
		actor = Actor("my_actor")
		assert actor.name == "my_actor"
		assert isinstance(actor.pool, QueuePool)
		assert actor.pool.size == 0
		assert isinstance(actor.logger, Logger)
		assert actor.logger.name == "my_actor"
		assert actor.convert_output == False

		actor = Actor("my_actor", size=1, convert_output=True)
		assert actor.pool.size == 1
		assert actor.convert_output == True

	#######################
	# connect_error_queue #
	#######################

	def test_connect_error_queue_1(self):
		#test default destination queue name
		self._test_queue(post_src_err=1, post_dest_in=1, test_inbox_name="error_inbox", 
			test_src_pool_name="error", test_outbox_name="outbox", test_dest_pool_name="inbound",
			func_name="connect_error_queue")

	def test_connect_error_queue_2(self):
		#test missing destination
		source_actor = MockActor(name='source_name')
		with self.assertRaises(AttributeError):
			source_actor.connect_error_queue()

	def test_connect_error_queue_3(self):
		#test destination queue name parameter
		self._test_queue(post_src_err=1, post_dest_in=1, test_inbox_name="error_destination_queue_name", 
			test_src_pool_name="error", test_outbox_name="outbox", test_dest_pool_name="inbound",
			destination_queue_name="destination_queue_name", func_name="connect_error_queue")

	#####################
	# connect_log_queue #
	#####################

	def test_connect_log_queue_1(self):
		#test default destination queue name
		self._test_queue(post_src_log=1, post_dest_in=1, test_inbox_name="log_inbox", 
			test_src_pool_name="logs", test_outbox_name="outbox", test_dest_pool_name="inbound",
			func_name="connect_log_queue")

	def test_connect_log_queue_2(self):
		#test missing destination
		source_actor = MockActor(name='source_name')
		with self.assertRaises(AttributeError):
			source_actor.connect_log_queue()

	def test_connect_log_queue_3(self):
		#test destination queue name parameter
		self._test_queue(post_src_log=1, post_dest_in=1, test_inbox_name="log_destination_queue_name", 
			test_src_pool_name="logs", test_outbox_name="outbox", test_dest_pool_name="inbound",
			destination_queue_name="destination_queue_name", func_name="connect_log_queue")

	#################
	# connect_queue #
	#################

	def test_connect_queue_1(self):
		#test default destination queue name
		self._test_queue(post_src_out=1, post_dest_in=1, test_inbox_name="inbox", 
			test_src_pool_name="outbound", test_outbox_name="outbox", test_dest_pool_name="inbound",
			func_name="connect_queue")

	def test_connect_queue_2(self):
		#test missing destination
		source_actor = MockActor(name='source_name')
		with self.assertRaises(AttributeError):
			source_actor.connect_queue()

	def test_connect_queue_3(self):
		#test destination queue name parameter
		self._test_queue(post_src_out=1, post_dest_in=1, test_inbox_name="destination_queue_name", 
			test_src_pool_name="outbound", test_outbox_name="outbox", test_dest_pool_name="inbound",
			destination_queue_name="destination_queue_name", func_name="connect_queue")

	#########################
	# _Actor__connect_queue #
	#########################

	def test__Actor__connect_queue_1(self):
		#test destination_queue_name
		self._test_queue(post_src_out=1, post_dest_in=1, test_inbox_name="destination_queue_name", 
			test_src_pool_name="outbound", test_outbox_name="outbox", test_dest_pool_name="inbound",
			destination_queue_name="destination_queue_name", func_name="_Actor__connect_queue",
			pool_scope_name="outbound")

	def test__Actor__connect_queue_2(self):
		#test empty destination_queue_name
		###TODO Queue with key None? Seems illogical to allow this but potentially damaging to dependent systems if altered
		source_actor, destination_actor = MockActor(name='source_name'), MockActor(name='destination_name')
		source_actor._Actor__connect_queue(destination=destination_actor, pool_scope=source_actor.pool.outbound, 
			destination_queue_name=None, source_queue_name="inbox", check_existing=False)
		self.assertEqual(source_actor.pool.outbound.get("inbox"), 
			destination_actor.pool.inbound.get(None))
		self.assertIsInstance(source_actor.pool.outbound.get("inbox"), Queue)

	def test__Actor__connect_queue_3(self):
		#test source_queue_name parameter
		self._test_queue(post_src_out=1, post_dest_in=1, test_inbox_name="inbox", 
			test_src_pool_name="outbound", test_outbox_name="source_queue_name", test_dest_pool_name="inbound",
			func_name="_Actor__connect_queue", pool_scope_name="outbound", source_queue_name="source_queue_name")

	def test__Actor__connect_queue_4(self):
		#test empty source_queue_name parameter
		###TODO Queue with key None? Seems illogical to allow this but potentially damaging to dependent systems if altered
		source_actor, destination_actor = MockActor(name='source_name'), MockActor(name='destination_name')
		source_actor._Actor__connect_queue(destination=destination_actor, pool_scope=source_actor.pool.outbound, 
			source_queue_name=None, destination_queue_name="outbox", check_existing=False)
		self.assertEqual(source_actor.pool.outbound.get(None), 
			destination_actor.pool.inbound.get("outbox"))
		self.assertIsInstance(source_actor.pool.outbound.get(None), Queue)

	def test__Actor__connect_queue_5(self):
		#test default/missing source_pool parameter
		with self.assertRaises(AttributeError):
			self._test_queue(post_src_out=1, post_dest_in=1, test_inbox_name="inbox", 
				test_src_pool_name="outbound", test_outbox_name="source_queue_name", test_dest_pool_name="inbound",
				func_name="_Actor__connect_queue", source_queue_name="source_queue_name")

	def test__Actor__connect_queue_6(self):
		#test missing destination
		source_actor = MockActor(name='source_name')
		with self.assertRaises(AttributeError):
			source_actor.connect_queue()

	def test__Actor__connect_queue_7(self):
		#test check_existing parameter existing source_queue
		source_actor, destination_actor = MockActor(name='source_name'), MockActor(name='destination_name')
		source_actor._Actor__connect_queue(destination=destination_actor, pool_scope=source_actor.pool.outbound, 
			destination_queue_name="outbox", source_queue_name="inbox", check_existing=True)
		with self.assertRaises(QueueConnected):
			source_actor._Actor__connect_queue(destination=destination_actor, pool_scope=source_actor.pool.outbound, 
				destination_queue_name="outbox2", source_queue_name="inbox", check_existing=True)

	def test__Actor__connect_queue_8(self):
		#test check_existing parameter existing destination_queue
		source_actor, destination_actor = MockActor(name='source_name'), MockActor(name='destination_name')
		source_actor._Actor__connect_queue(destination=destination_actor, pool_scope=source_actor.pool.outbound, 
			destination_queue_name="outbox", source_queue_name="inbox", check_existing=True)
		with self.assertRaises(QueueConnected):
			source_actor._Actor__connect_queue(destination=destination_actor, pool_scope=source_actor.pool.outbound, 
				destination_queue_name="outbox", source_queue_name="inbox2", check_existing=True)

	def test__Actor__connect_queue_9(self):
		#test missing source_queue missing destination queue
		source_actor, destination_actor = MockActor(name='source_name'), MockActor(name='destination_name')
		self._test_pool(actor=source_actor, error=0, inbound=0, outbound=0, logs=1)
		self._test_pool(actor=destination_actor, error=0, inbound=0, outbound=0, logs=1)
		source_actor._Actor__connect_queue(destination=destination_actor, pool_scope=source_actor.pool.outbound, 
			destination_queue_name="outbox", source_queue_name="inbox", check_existing=False)
		self._test_pool(actor=source_actor, error=0, inbound=0, outbound=1, logs=1)
		self._test_pool(actor=destination_actor, error=0, inbound=1, outbound=0, logs=1)
		self.assertEqual(destination_actor.pool.inbound.get("outbox"), source_actor.pool.outbound.get("inbox"))
		self.assertIsInstance(destination_actor.pool.inbound.get("outbox"), Queue)

	def test__Actor__connect_queue_10(self):
		#test missing source_queue existing destination queue
		source_actor, destination_actor = MockActor(name='source_name'), MockActor(name='destination_name')
		self._test_pool(actor=source_actor, error=0, inbound=0, outbound=0, logs=1)
		self._test_pool(actor=destination_actor, error=0, inbound=0, outbound=0, logs=1)
		source_actor._Actor__connect_queue(destination=destination_actor, pool_scope=source_actor.pool.outbound, 
			destination_queue_name="outbox", source_queue_name="inbox", check_existing=False)
		self._test_pool(actor=source_actor, error=0, inbound=0, outbound=1, logs=1)
		self._test_pool(actor=destination_actor, error=0, inbound=1, outbound=0, logs=1)
		source_actor._Actor__connect_queue(destination=destination_actor, pool_scope=source_actor.pool.outbound, 
			destination_queue_name="outbox", source_queue_name="inbox2", check_existing=False)
		self._test_pool(actor=source_actor, error=0, inbound=0, outbound=2, logs=1)
		self._test_pool(actor=destination_actor, error=0, inbound=1, outbound=0, logs=1)
		self.assertEqual(destination_actor.pool.inbound.get("outbox"), source_actor.pool.outbound.get("inbox"))
		self.assertEqual(destination_actor.pool.inbound.get("outbox"), source_actor.pool.outbound.get("inbox2"))
		self.assertIsInstance(destination_actor.pool.inbound.get("outbox"), Queue)

	def test__Actor__connect_queue_11(self):
		#test existing source_queue missing destination queue
		source_actor, destination_actor = MockActor(name='source_name'), MockActor(name='destination_name')
		self._test_pool(actor=source_actor, error=0, inbound=0, outbound=0, logs=1)
		self._test_pool(actor=destination_actor, error=0, inbound=0, outbound=0, logs=1)
		source_actor._Actor__connect_queue(destination=destination_actor, pool_scope=source_actor.pool.outbound, 
			destination_queue_name="outbox", source_queue_name="inbox", check_existing=False)
		self._test_pool(actor=source_actor, error=0, inbound=0, outbound=1, logs=1)
		self._test_pool(actor=destination_actor, error=0, inbound=1, outbound=0, logs=1)
		source_actor._Actor__connect_queue(destination=destination_actor, pool_scope=source_actor.pool.outbound, 
			destination_queue_name="outbox2", source_queue_name="inbox", check_existing=False)
		self._test_pool(actor=source_actor, error=0, inbound=0, outbound=1, logs=1)
		self._test_pool(actor=destination_actor, error=0, inbound=2, outbound=0, logs=1)
		self.assertEqual(destination_actor.pool.inbound.get("outbox"), source_actor.pool.outbound.get("inbox"))
		self.assertEqual(destination_actor.pool.inbound.get("outbox2"), source_actor.pool.outbound.get("inbox"))
		self.assertIsInstance(destination_actor.pool.inbound.get("outbox"), Queue)

	def test__Actor__connect_queue_12(self):
		#test existing source_queue existing destination queue
		source_actor, destination_actor = MockActor(name='source_name'), MockActor(name='destination_name')
		self._test_pool(actor=source_actor, error=0, inbound=0, outbound=0, logs=1)
		self._test_pool(actor=destination_actor, error=0, inbound=0, outbound=0, logs=1)
		source_actor._Actor__connect_queue(destination=destination_actor, pool_scope=source_actor.pool.outbound, 
			destination_queue_name="outbox", source_queue_name="inbox", check_existing=False)
		self._test_pool(actor=source_actor, error=0, inbound=0, outbound=1, logs=1)
		self._test_pool(actor=destination_actor, error=0, inbound=1, outbound=0, logs=1)
		source_actor._Actor__connect_queue(destination=destination_actor, pool_scope=source_actor.pool.outbound, 
			destination_queue_name="outbox", source_queue_name="inbox", check_existing=False)
		self._test_pool(actor=source_actor, error=0, inbound=0, outbound=1, logs=1)
		self._test_pool(actor=destination_actor, error=0, inbound=1, outbound=0, logs=1)
		self.assertEqual(destination_actor.pool.inbound.get("outbox"), source_actor.pool.outbound.get("inbox"))
		self.assertIsInstance(destination_actor.pool.inbound.get("outbox"), Queue)

	#############################
	# _Actor__register_consumer #
	#############################

	def test__Actor__register_consumer_1(self):
		#test spawn_thread call
		MockedActor = funcs_tester(clazz=MockActor, func_definitions={"spawn_thread":None})
		actor, queue = MockedActor(name='actor_name'), Queue("test_queue")
		self.assertEqual(len(actor.pool.inbound), 0)
		_test_func(self=self, obj=actor, func_name="spawn_thread", did=False, args=None, kwargs=None)
		actor._Actor__register_consumer(queue_name="test_name", queue=queue)
		self.assertEqual(len(actor.pool.inbound), 1)
		_test_func(self=self, obj=actor, func_name="spawn_thread", did=True, args=tuple(), kwargs={"run":actor._Actor__consumer, "origin_queue":queue}, count=1)

	def test__Actor__register_consumer_2(self):
		#test __consumer threading
		MockedActor = funcs_tester(clazz=MockActor, func_definitions={"_Actor__consumer":None})
		actor, queue = MockedActor(name='actor_name'), Queue("test_queue")
		self.assertEqual(len(actor.pool.inbound), 0)
		_test_func(self=self, obj=actor, func_name="_Actor__consumer", did=False, args=None, kwargs=None)
		actor._Actor__register_consumer(queue_name="test_name", queue=queue)
		self.assertEqual(len(actor.pool.inbound), 1)
		_test_func(self=self, obj=actor, func_name="_Actor__consumer", did=False, args=None, kwargs=None)
		actor.start()
		sleep(0)
		self.assertEqual(len(actor.pool.inbound), 1)
		_test_func(self=self, obj=actor, func_name="_Actor__consumer", did=True, args=tuple(), kwargs={"origin_queue":queue}, count=1)

	#########
	# start #
	#########

	def test_start_1(self):
		#baseline doesn't break
		actor = MockActor(name='actor_name')
		self.assertEqual(getattr(actor, "pre_hook", None), None)
		actor.start()

	def test_start_2(self):
		#running
		actor = MockActor(name='actor_name')
		self.assertEqual(actor.is_running(), False)
		actor.start()
		self.assertEqual(actor.is_running(), True)

	def test_start_3(self):
		#success
		MockedActor = funcs_tester(clazz=MockActor, func_definitions={'pre_hook':None})
		actor = MockedActor(name='actor_name')
		_test_func(self=self, obj=actor, func_name="pre_hook", did=False, args=None, kwargs=None)
		actor.start()
		_test_func(self=self, obj=actor, func_name="pre_hook", did=True, args=tuple(), kwargs=dict(), count=1)

	########
	# stop #
	########

	def test_stop_1(self):
		#baseline (doesn't break)
		actor = MockActor(name='actor_name')
		self.assertEqual(getattr(actor, "post_hook", None), None)
		actor.stop()

	def test_stop_2(self):
		#success
		MockedActor = funcs_tester(clazz=MockActor, func_definitions={'post_hook':None})
		actor = MockedActor(name='actor_name')
		_test_func(self=self, obj=actor, func_name="post_hook", did=False, args=None, kwargs=None)
		actor.stop()
		_test_func(self=self, obj=actor, func_name="post_hook", did=True, args=tuple(), kwargs=dict(), count=1)

	######################
	# _Actor__send_event #
	######################

	def test__Actor__send_event_1(self):
		#test none queues
		MockedActor = funcs_tester(clazz=MockActor, func_definitions={"_Actor__loop_send":None})
		actor, queue, event = MockedActor(name='actor_name'), Queue("test_queue"), Event()
		actor.pool.outbound.add(name=queue.name, queue=queue)
		_test_func(self=self, obj=actor, func_name="_Actor__loop_send", did=False, args=None, kwargs=None)
		actor._Actor__send_event(event=event)
		_test_func(self=self, obj=actor, func_name="_Actor__loop_send", did=True, args=tuple(), kwargs={"event":event, "destination_queues":actor.pool.outbound}, count=1)

	def test__Actor__send_event_2(self):
		#test provided queues
		MockedActor = funcs_tester(clazz=MockActor, func_definitions={"_Actor__loop_send":None})
		actor, queue, event = MockedActor(name='actor_name'), Queue("test_queue2"), Event()
		_test_func(self=self, obj=actor, func_name="_Actor__loop_send", did=False, args=None, kwargs=None)
		actor._Actor__send_event(event=event, destination_queues=[queue])
		_test_func(self=self, obj=actor, func_name="_Actor__loop_send", did=True, args=tuple(), kwargs={"event":event, "destination_queues":[queue]}, count=1)

	######################
	# _Actor__send_error #
	######################

	def test__Actor__send_error(self):
		MockedActor = funcs_tester(clazz=MockActor, func_definitions={"_Actor__loop_send":None})
		actor, queue, event = MockedActor(name='actor_name'), Queue("test_queue"), Event()
		actor.pool.error.add(name=queue.name, queue=queue)
		_test_func(self=self, obj=actor, func_name="_Actor__loop_send", did=False, args=None, kwargs=None)
		actor._Actor__send_error(event=event)
		_test_func(self=self, obj=actor, func_name="_Actor__loop_send", did=True, args=tuple(), kwargs={"event":event, "destination_queues":actor.pool.error}, count=1)

	#####################
	# _Actor__loop_send #
	#####################

	def test__Actor__loop_send_1(self):
		#dict queues, single queue
		MockedActor = funcs_tester(clazz=MockActor)
		actor, event, queues = MockedActor(name='actor_name'), Event(), [Queue("test_queue1")]
		queues = {queue.name: queue for queue in queues}
		self.assertEqual(len(queues), 1)		
		for queue in queues.itervalues():
			self.assertEqual(len(queue), 0)		
		actor._Actor__loop_send(event=event, destination_queues=queues)
		for queue in queues.itervalues():
			self.assertEqual(len(queue), 1)
		queued_events = [queue.get() for queue in queues.itervalues()]
		exists = event in queued_events
		singles = remove_dupes(queued_events)
		self.assertEqual(exists, True)
		self.assertEqual(len(singles) == len(queued_events), True)

	def test__Actor__loop_send_2(self):
		#dict queues, multi queues
		actor, event, queues = MockedActor(name='actor_name'), Event(), [Queue("test_queue1"), Queue("test_queue2")]
		queues = {queue.name: queue for queue in queues}
		self.assertEqual(len(queues), 2)		
		for queue in queues.itervalues():
			self.assertEqual(len(queue), 0)		
		actor._Actor__loop_send(event=event, destination_queues=queues)
		for queue in queues.itervalues():
			self.assertEqual(len(queue), 1)
		queued_events = [queue.get() for queue in queues.itervalues()]
		exists = event in queued_events
		singles = remove_dupes(queued_events)
		self.assertEqual(exists, False)
		self.assertEqual(len(singles) == len(queued_events), True)

	def test__Actor__loop_send_3(self):
		#list queues, single queue
		actor, event, queues = MockedActor(name='actor_name'), Event(), [Queue("test_queue1")]
		self.assertEqual(len(queues), 1)		
		for queue in queues:
			self.assertEqual(len(queue), 0)		
		actor._Actor__loop_send(event=event, destination_queues=queues)
		for queue in queues:
			self.assertEqual(len(queue), 1)
		queued_events = [queue.get() for queue in queues]
		exists = event in queued_events
		singles = remove_dupes(queued_events)
		self.assertEqual(exists, True)
		self.assertEqual(len(singles) == len(queued_events), True)

	def test__Actor__loop_send_4(self):
		#list queues, mutli queues
		actor, event, queues = MockedActor(name='actor_name'), Event(), [Queue("test_queue1"), Queue("test_queue2")]
		self.assertEqual(len(queues), 2)		
		for queue in queues:
			self.assertEqual(len(queue), 0)		
		actor._Actor__loop_send(event=event, destination_queues=queues)
		for queue in queues:
			self.assertEqual(len(queue), 1)
		queued_events = [queue.get() for queue in queues]
		exists = event in queued_events
		singles = remove_dupes(queued_events)
		self.assertEqual(exists, False)
		self.assertEqual(len(singles) == len(queued_events), True)


	#############################
	# _Actor__generate_split_id #
	#############################

	def test__Actor__generate_split_id(self):
		MockedActor = funcs_tester(clazz=MockActor)
		actor1, event1 = MockedActor(name='actor_name1'), Event()
		actor2, event2 = MockedActor(name='actor_name2'), Event()
		id1 = actor1._Actor__generate_split_id(event=event1)
		id2 = actor1._Actor__generate_split_id(event=event2)
		id3 = actor2._Actor__generate_split_id(event=event1)
		id4 = actor2._Actor__generate_split_id(event=event2)
		id5 = actor2._Actor__generate_split_id(event=event2)
		self.assertNotEqual(id1, id2)
		self.assertNotEqual(id1, id3)
		self.assertNotEqual(id1, id4)
		self.assertNotEqual(id2, id3)
		self.assertNotEqual(id2, id4)
		self.assertNotEqual(id3, id4)
		self.assertEqual(id4, id5)
		sleep(1)
		id6 = actor2._Actor__generate_split_id(event=event2)
		self.assertNotEqual(id4, id6)

	####################
	# _Actor__consumer #
	####################

	def test__Actor__consumer_1(self):
		#test spawn
		MockedActor = funcs_tester(clazz=MockActor, func_definitions={"_Actor__consumer":None})
		actor = MockedActor(name='something_else')
		_test_func(self=self, obj=actor, func_name="_Actor__consumer", did=False, args=None, kwargs=None)
		get_restart_pool().spawn(actor._Actor__consumer)
		_test_func(self=self, obj=actor, func_name="_Actor__consumer", did=False, args=None, kwargs=None)
		sleep(0)
		_test_func(self=self, obj=actor, func_name="_Actor__consumer", did=True, args=tuple(), kwargs=dict(), count=1)

	def test__Actor__consumer_2(self):
		#test start then add event
		MockedActor = funcs_tester(clazz=MockActor, func_definitions={"_Actor__try_spawn_consume":None})
		actor, event, queue = MockedActor(name='actor_name'), Event(), Queue("queue_name")
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		get_restart_pool().spawn(actor._Actor__consumer, origin_queue=queue)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		self.assertEqual(actor.is_running(), False)
		actor.start()
		self.assertEqual(actor.is_running(), True)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		sleep()
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		queue.put(event)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		sleep()
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=True, args=tuple(), kwargs={"origin_queue":queue, "timeout":10}, count=1)

	def test__Actor__consumer_3(self):
		#test add event then start
		MockedActor = funcs_tester(clazz=MockActor, func_definitions={"_Actor__try_spawn_consume":None})
		actor, event, queue = MockedActor(name='actor_name'), Event(), Queue("queue_name")
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		get_restart_pool().spawn(actor._Actor__consumer, origin_queue=queue)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		queue.put(event)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		sleep()
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		self.assertEqual(actor.is_running(), False)
		actor.start()
		self.assertEqual(actor.is_running(), True)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		sleep()
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=True, args=tuple(), kwargs={"origin_queue":queue, "timeout":10}, count=1)

	def test__Actor__consumer_4(self):
		#test start, add_event, stop
		MockedActor = funcs_tester(clazz=MockActor, func_definitions={"_Actor__try_spawn_consume":None})
		actor, event, queue = MockedActor(name='actor_name'), Event(), Queue("queue_name")
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		get_restart_pool().spawn(actor._Actor__consumer, origin_queue=queue)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		self.assertEqual(actor.is_running(), False)
		actor.start()
		self.assertEqual(actor.is_running(), True)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		sleep(0)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		queue.put(event)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		self.assertEqual(actor.is_running(), True)
		actor.stop()
		self.assertEqual(actor.is_running(), False)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=True, args=tuple(), kwargs={"origin_queue":queue, "timeout":10}, count=1)

	def test__Actor__consumer_5(self):
		#test start, stop, add_event
		MockedActor = funcs_tester(clazz=MockActor, func_definitions={"_Actor__try_spawn_consume":None})
		actor, event, queue = MockedActor(name='actor_name'), Event(), Queue("queue_name")
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		get_restart_pool().spawn(actor._Actor__consumer, origin_queue=queue)
		sleep(0)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		self.assertEqual(actor.is_running(), False)
		actor.start()
		self.assertEqual(actor.is_running(), True)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		sleep(0)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		self.assertEqual(actor.is_running(), True)
		actor.stop()
		self.assertEqual(actor.is_running(), False)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		sleep(0)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		queue.put(event)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		sleep(0)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)

	def test__Actor__consumer_6(self):
		#test start, add_event, stop, reset, start
		MockedActor = funcs_tester(clazz=MockActor, func_definitions={"_Actor__try_spawn_consume":None})
		actor, event, queue = MockedActor(name='actor_name'), Event(), Queue("queue_name")
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		get_restart_pool().spawn(run=actor._Actor__consumer, origin_queue=queue)
		actor.start()
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		sleep(0)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		queue.put(event)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		self.assertEqual(actor.is_running(), True)
		actor.stop()
		self.assertEqual(actor.is_running(), False)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=True, args=tuple(), kwargs={"origin_queue":queue, "timeout":10}, count=1)
		func_name = "_Actor__try_spawn_consume"
		did_attr_name = "did_%s" % func_name
		args_attr_name = "args_%s" % func_name
		kwargs_attr_name = "kwargs_%s" % func_name
		count_attr_name = "count_%s" % func_name
		setattr(actor, did_attr_name, False)
		setattr(actor, args_attr_name, None)
		setattr(actor, kwargs_attr_name, None)
		setattr(actor, count_attr_name, 0)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		self.assertEqual(actor.is_running(), False)
		actor.start()
		self.assertEqual(actor.is_running(), True)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=False, args=None, kwargs=None)
		sleep(0)
		_test_func(self=self, obj=actor, func_name="_Actor__try_spawn_consume", did=True, args=tuple(), kwargs={"origin_queue":queue, "timeout":10}, count=1)

	#############################
	# _Actor__try_spawn_consume #
	#############################

	def test__Actor__try_spawn_consume(self):
		MockedActor = funcs_tester(clazz=MockActor, func_definitions={"spawn_thread":None})
		actor, queue, event = MockedActor(name='actor_name'), Queue("queue_name"), Event()
		_test_func(self=self, obj=actor, func_name="spawn_thread", did=False, args=None, kwargs=None)
		actor._Actor__try_spawn_consume(origin_queue=queue)
		_test_func(self=self, obj=actor, func_name="spawn_thread", did=False, args=None, kwargs=None)
		queue.put(event)
		_test_func(self=self, obj=actor, func_name="spawn_thread", did=False, args=None, kwargs=None)
		actor._Actor__try_spawn_consume(origin_queue=queue)
		_test_func(self=self, obj=actor, func_name="spawn_thread", did=True, args=tuple(), kwargs={"run":actor._Actor__do_consume, "event":event, "origin_queue":queue, "graceful_restart":False, "irregular_restart":False}, count=1)

	##################################
	# _Actor__consume_pre_processing #
	##################################

	def test__Actor__consume_pre_processing_1(self):
		#test convert
		actor, event = MockedActor(name='actor_name'), Event()
		actor.input = HttpEvent
		event.data = "hello"
		new_event = actor._Actor__consume_pre_processing(event=event, origin_queue=Queue("queue_name"))
		self.assertEqual(new_event.data, "hello")
		self.assertNotEqual(event, new_event)
		self.assertEqual(isinstance(new_event, HttpEvent), True)

	def test__Actor__consume_pre_processing_2(self):
		#test convert error
		actor, event = MockedActor(name='actor_name'), XMLEvent()
		actor.input = JSONEvent
		event._data = "hello"
		with self.assertRaises(InvalidEventConversion):
			new_event = actor._Actor__consume_pre_processing(event=event, origin_queue=Queue("queue_name"))

	def test__Actor__consume_pre_processing_3(self):
		#test required_attrs success
		actor, event = MockedActor(name='actor_name'), Event()
		actor.REQUIRED_EVENT_ATTRIBUTES = ["soap", "nada"]
		event.soap = "exists"
		event.nada = "also exists"
		new_event = actor._Actor__consume_pre_processing(event=event, origin_queue=Queue("queue_name"))

	def test__Actor__consume_pre_processing_4(self):
		#test required_attrs fail
		actor, event = MockedActor(name='actor_name'), Event()
		actor.REQUIRED_EVENT_ATTRIBUTES = ["soap", "nada"]
		with self.assertRaises(InvalidActorInput):
			new_event = actor._Actor__consume_pre_processing(event=event, origin_queue=Queue("queue_name"))
		
	def test__Actor__consume_pre_processing_5(self):
		#test timeout_check
		actor, event = MockedActor(name='actor_name'), funcs_tester(clazz=Event, func_definitions={"timeout_check":None})()
		actor.input = event.__class__
		_test_func(self=self, obj=event, func_name="timeout_check", did=False, args=None, kwargs=None)
		new_event = actor._Actor__consume_pre_processing(event=event, origin_queue=Queue("queue_name"))
		_test_func(self=self, obj=new_event, func_name="timeout_check", did=True, args=tuple(), kwargs=dict(), count=1)

	###################################
	# _Actor__consume_post_processing #
	###################################

	def test__Actor__consume_post_processing_1(self):
		#test convert
		MockedActor = funcs_tester(clazz=MockActor)
		actor, event = MockedActor(name='actor_name'), Event()
		actor.output = HttpEvent
		actor.convert_output = True
		event.data = "hello"
		new_event = actor._Actor__consume_post_processing(event=event, destination_queues=Queue("queue_name"))
		self.assertEqual(new_event.data, "hello")
		self.assertNotEqual(event, new_event)
		self.assertEqual(isinstance(new_event, HttpEvent), True)

	def test__Actor__consume_post_processing_2(self):
		#test output mismatch without conversion
		actor, event = MockedActor(name='actor_name'), Event()
		actor.output = HttpEvent
		event.data = "hello"
		with self.assertRaises(InvalidActorOutput):
			new_event = actor._Actor__consume_post_processing(event=event, destination_queues=Queue("queue_name"))
		
	def test__Actor__consume_post_processing_3(self):
		#test convert error
		actor, event = MockedActor(name='actor_name'), XMLEvent()
		actor.output = JSONEvent
		event._data = "hello"
		actor.convert_output = True
		with self.assertRaises(InvalidActorOutput):
			new_event = actor._Actor__consume_post_processing(event=event, destination_queues=Queue("queue_name"))

	def test__Actor__consume_post_processing_4(self):
		#test timeout_check
		actor, event = MockedActor(name='actor_name'), funcs_tester(clazz=Event, func_definitions={"timeout_check":None})()
		actor.output = event.__class__
		_test_func(self=self, obj=event, func_name="timeout_check", did=False, args=None, kwargs=None)
		new_event = actor._Actor__consume_post_processing(event=event, destination_queues=Queue("queue_name"))
		_test_func(self=self, obj=new_event, func_name="timeout_check", did=True, args=tuple(), kwargs=dict(), count=1)

	###########################
	# _Actor__consume_wrapper #
	###########################

	def test__Actor__consume_wrapper_1(self):
		#test consume
		event, queue = Event(), Queue("queue_name")
		actor = funcs_tester(clazz=MockActor, func_definitions={"consume": event, "_Actor__format_event": None, "_Actor__format_queues": None})(name='actor_name')
		_test_func(self=self, obj=actor, func_name="consume", did=False, args=None, kwargs=None)
		actor._Actor__consume_wrapper(event=event, origin_queue=queue)
		_test_func(self=self, obj=actor, func_name="consume", did=True, args=tuple(), kwargs={"event":event, "origin_queue":queue}, count=1)

	def test__Actor__consume_wrapper_2(self):
		#test returns 1
		event, queue = Event(), Queue("queue_name")
		actor = funcs_tester(clazz=MockActor, func_definitions={"consume": event, "_Actor__format_event": None, "_Actor__format_queues": None})(name='actor_name')
		_test_func(self=self, obj=actor, func_name="consume", did=False, args=None, kwargs=None)
		actor._Actor__consume_wrapper(event=event, origin_queue=queue)
		_test_func(self=self, obj=actor, func_name="consume", did=True, args=tuple(), kwargs={"event":event, "origin_queue":queue}, count=1)

	def test__Actor__consume_wrapper_3(self):
		#test returns 2
		event, queue = Event(), Queue("queue_name")
		actor = funcs_tester(clazz=MockActor, func_definitions={"consume": (event, queue), "_Actor__format_event": None, "_Actor__format_queues": None})(name='actor_name')
		_test_func(self=self, obj=actor, func_name="consume", did=False, args=None, kwargs=None)
		actor._Actor__consume_wrapper(event=event, origin_queue=queue)
		_test_func(self=self, obj=actor, func_name="consume", did=True, args=tuple(), kwargs={"event":event, "origin_queue":queue}, count=1)

	def test__Actor__consume_wrapper_4(self):
		#test returns 3
		event, queue = Event(), Queue("queue_name")
		actor = funcs_tester(clazz=MockActor, func_definitions={"consume": (event, queue, None), "_Actor__format_event": None, "_Actor__format_queues": None})(name='actor_name')
		_test_func(self=self, obj=actor, func_name="consume", did=False, args=None, kwargs=None)
		actor._Actor__consume_wrapper(event=event, origin_queue=queue)
		_test_func(self=self, obj=actor, func_name="consume", did=True, args=tuple(), kwargs={"event":event, "origin_queue":queue}, count=1)

	def test__Actor__consume_wrapper_5(self):
		#test formats
		event, queue = Event(), Queue("queue_name")
		actor = funcs_tester(clazz=MockActor, func_definitions={"consume": (event, queue), "_Actor__format_event": None, "_Actor__format_queues": None})(name='actor_name')
		_test_func(self=self, obj=actor, func_name="consume", did=False, args=None, kwargs=None)
		_test_func(self=self, obj=actor, func_name="_Actor__format_event", did=False, args=None, kwargs=None)
		_test_func(self=self, obj=actor, func_name="_Actor__format_queues", did=False, args=None, kwargs=None)
		actor._Actor__consume_wrapper(event=event, origin_queue=queue)
		_test_func(self=self, obj=actor, func_name="consume", did=True, args=tuple(), kwargs={"event":event, "origin_queue":queue}, count=1)
		_test_func(self=self, obj=actor, func_name="_Actor__format_event", did=True, args=tuple(), kwargs={"event":event}, count=1)
		_test_func(self=self, obj=actor, func_name="_Actor__format_queues", did=True, args=tuple(), kwargs={"queues":queue}, count=1)

	######################
	# _Actor__do_consume # X
	######################

	def test__Actor__do_consume_1(self):
		#test success no event
		event, queue = Event(), Queue("queue_name")
		defs = {"_Actor__consume_pre_processing": 1,"_Actor__consume_wrapper": (2, 3), "_Actor__consume_post_processing": None, "_Actor__send_event": 5}
		actor = funcs_tester(clazz=MockActor, func_definitions=defs)(name='actor_name')
		_test_func(self=self, obj=actor, func_name="_Actor__consume_pre_processing", did=False, args=None, kwargs=None)
		_test_func(self=self, obj=actor, func_name="_Actor__consume_wrapper", did=False, args=None, kwargs=None)
		_test_func(self=self, obj=actor, func_name="_Actor__consume_post_processing", did=False, args=None, kwargs=None)
		_test_func(self=self, obj=actor, func_name="_Actor__send_event", did=False, args=None, kwargs=None)
		actor._Actor__do_consume(event=event, origin_queue=queue)
		_test_func(self=self, obj=actor, func_name="_Actor__consume_pre_processing", did=True, args=tuple(), kwargs={"event":event, "origin_queue": queue}, count=1)
		_test_func(self=self, obj=actor, func_name="_Actor__consume_wrapper", did=True, args=tuple(), kwargs={"event":1, "origin_queue": queue}, count=1)
		_test_func(self=self, obj=actor, func_name="_Actor__consume_post_processing", did=True, args=tuple(), kwargs={"event":2, "destination_queues":3}, count=1)
		_test_func(self=self, obj=actor, func_name="_Actor__send_event", did=False, args=None, kwargs=None)
	
	def test__Actor__do_consume_2(self):
		#test success with event
		event, queue = Event(), Queue("queue_name")
		defs = {"_Actor__consume_pre_processing": 1,"_Actor__consume_wrapper": (2, 3), "_Actor__consume_post_processing": event, "_Actor__send_event": 5}
		actor = funcs_tester(clazz=MockActor, func_definitions=defs)(name='actor_name')
		_test_func(self=self, obj=actor, func_name="_Actor__consume_pre_processing", did=False, args=None, kwargs=None)
		_test_func(self=self, obj=actor, func_name="_Actor__consume_wrapper", did=False, args=None, kwargs=None)
		_test_func(self=self, obj=actor, func_name="_Actor__consume_post_processing", did=False, args=None, kwargs=None)
		_test_func(self=self, obj=actor, func_name="_Actor__send_event", did=False, args=None, kwargs=None)
		actor._Actor__do_consume(event=event, origin_queue=queue)
		_test_func(self=self, obj=actor, func_name="_Actor__consume_pre_processing", did=True, args=tuple(), kwargs={"event":event, "origin_queue": queue}, count=1)
		_test_func(self=self, obj=actor, func_name="_Actor__consume_wrapper", did=True, args=tuple(), kwargs={"event":1, "origin_queue": queue}, count=1)
		_test_func(self=self, obj=actor, func_name="_Actor__consume_post_processing", did=True, args=tuple(), kwargs={"event":2, "destination_queues":3}, count=1)
		_test_func(self=self, obj=actor, func_name="_Actor__send_event", did=True, args=tuple(), kwargs={"event":event, "destination_queues":3}, count=1)

	def test__Actor__do_consume_3(self):
		#test QueueFull with wait
		event1, event2 = Event(), Event()
		MockedQueue = funcs_tester(clazz=Queue)
		queue = MockedQueue("queue_name", maxsize=1)
		old_put = queue.put
		queue.put = lambda element: old_put(element=element, block=False)
		self.assertEqual(queue.qsize(), 0)
		self.assertEqual(queue.maxsize, 1)
		queue.put(event2)
		self.assertEqual(queue.qsize(), 1)
		self.assertEqual(queue.maxsize, 1)
		defs = {"_Actor__consume_pre_processing": 1,"_Actor__consume_wrapper": (2, [queue]), "_Actor__consume_post_processing": event1}
		actor = funcs_tester(clazz=MockActor, func_definitions=defs)(name='actor_name')
		_test_func(self=self, obj=actor, func_name="_Actor__consume_pre_processing", did=False, args=None, kwargs=None)
		_test_func(self=self, obj=actor, func_name="_Actor__consume_wrapper", did=False, args=None, kwargs=None)
		_test_func(self=self, obj=actor, func_name="_Actor__consume_post_processing", did=False, args=None, kwargs=None)
		actor.spawn_thread(run=actor._Actor__do_consume, event=event1, origin_queue=queue)
		_test_func(self=self, obj=actor, func_name="_Actor__consume_pre_processing", did=False, args=None, kwargs=None)
		_test_func(self=self, obj=actor, func_name="_Actor__consume_wrapper", did=False, args=None, kwargs=None)
		_test_func(self=self, obj=actor, func_name="_Actor__consume_post_processing", did=False, args=None, kwargs=None)
		actor.start()
		sleep(0)
		_test_func(self=self, obj=actor, func_name="_Actor__consume_pre_processing", did=True, args=tuple(), kwargs={"event":event1, "origin_queue": queue}, count=1)
		_test_func(self=self, obj=actor, func_name="_Actor__consume_wrapper", did=True, args=tuple(), kwargs={"event":1, "origin_queue": queue}, count=1)
		_test_func(self=self, obj=actor, func_name="_Actor__consume_post_processing", did=True, args=tuple(), kwargs={"event":2, "destination_queues":[queue]}, count=1)
	
	def test__Actor__do_consume_4(self):
		#test QueueFull without wait
		event1, event2 = Event(), Event()
		MockedQueue = funcs_tester(clazz=Queue, func_definitions={"wait_until_free":None})
		queue = MockedQueue("queue_name", maxsize=1)
		old_put = queue.put
		queue.put = lambda element: old_put(element=element, block=False)
		self.assertEqual(queue.qsize(), 0)
		self.assertEqual(queue.maxsize, 1)
		queue.put(event2)
		self.assertEqual(queue.qsize(), 1)
		self.assertEqual(queue.maxsize, 1)
		defs = {"_Actor__consume_pre_processing": 1,"_Actor__consume_wrapper": (2, [queue]), "_Actor__consume_post_processing": event1}
		actor = funcs_tester(clazz=MockActor, func_definitions=defs)(name='actor_name')
		_test_func(self=self, obj=actor, func_name="_Actor__consume_pre_processing", did=False, args=None, kwargs=None)
		_test_func(self=self, obj=actor, func_name="_Actor__consume_wrapper", did=False, args=None, kwargs=None)
		_test_func(self=self, obj=actor, func_name="_Actor__consume_post_processing", did=False, args=None, kwargs=None)
		_test_func(self=self, obj=queue, func_name="wait_until_free", did=False, args=None, kwargs=None)
		with self.assertRaises(QueueFull):
			actor._Actor__do_consume(event=event1, origin_queue=queue)

	def test__Actor__do_consume_5(self):
		#test send error
		event = Event()
		defs = {"_Actor__consume_pre_processing": 1,"_Actor__consume_wrapper": (event, None), "_Actor__send_error": None}
		actor = funcs_tester(clazz=MockActor, func_definitions=defs)(name='actor_name')
		actor._Actor__consume_post_processing = raise_exception_func(exception=Exception)
		_test_func(self=self, obj=actor, func_name="_Actor__send_error", did=False, args=None, kwargs=None)
		actor._Actor__do_consume(event=event, origin_queue=None)
		_test_func(self=self, obj=actor, func_name="_Actor__send_error", did=True, args=tuple(), kwargs={"event":event}, count=1)

	def test__Actor__do_consume_6(self):
		#as is
		event1, event2, in_queue, out_queue = Event(), Event(), Queue(name="in_queue_name"), Queue(name="out_queue_name")
		class MockedActor(Actor):
			def consume(self, event, *args, **kwargs):
				return event2, out_queue
		actor = MockedActor(name='actor_name')
		self.assertEqual(in_queue.qsize(), 0)
		in_queue.put(element=event1)
		self.assertEqual(in_queue.qsize(), 1)
		self.assertEqual(out_queue.qsize(), 0)
		actor._Actor__do_consume(event=event1, origin_queue=in_queue)
		self.assertEqual(out_queue.qsize(), 1)
		self.assertEqual(out_queue.get(), event2)

	################
	# create_event # X
	################

	def test_create_event_1(self):
		#success
		actor = MockedActor(name="actor_name")
		actor.output = Event
		event = actor.create_event()
		self.assertEquals(isinstance(event, Event), True)

	def test_create_event_2(self):
		#fail
		actor = MockedActor(name="actor_name")
		actor.output = "test"
		with self.assertRaises(ValueError):
			actor.create_event()

	########################
	# _Actor__format_event # X
	########################

	def test__Actor__format_event_1(self):
		#success with Event
		actor, event = MockedActor(name="actor_name"), Event()
		new_event = actor._Actor__format_event(event=event)
		self.assertEquals(new_event, event)

	def test__Actor__format_event_2(self):
		#success with None
		actor, event = MockedActor(name="actor_name"), None
		new_event = actor._Actor__format_event(event=event)
		self.assertEquals(new_event, event)

	def test__Actor__format_event_3(self):
		#fail
		actor, event = MockedActor(name="actor_name"), "not and event"
		with self.assertRaises(PypesException):
			new_event = actor._Actor__format_event(event=event)

	#########################
	# _Actor__format_queues # X
	#########################

	def test__Actor__format_queues_1(self):
		#queues as dict with valid queue values
		actor, queue = MockedActor(name="actor_name"), Queue(name="queue_name")
		queues = actor._Actor__format_queues(queues={"queue_name": queue})
		self.assertEquals(queues, [queue])

	def test__Actor__format_queues_2(self):
		#queues as dict without valid queue values
		actor, queue = MockedActor(name="actor_name"), "definitely_not_a_queue"
		with self.assertRaises(PypesException):
			queues = actor._Actor__format_queues(queues={"queue_name": queue})

	def test__Actor__format_queues_3(self):
		#queues as tuple with valid queue values
		actor, queue = MockedActor(name="actor_name"), Queue(name="queue_name")
		queues = actor._Actor__format_queues(queues=(queue,))
		self.assertEquals(queues, [queue])

	def test__Actor__format_queues_4(self):
		#queues as tuple without valid queue values
		actor, queue = MockedActor(name="actor_name"), "definitely_not_a_queue"
		with self.assertRaises(PypesException):
			queues = actor._Actor__format_queues(queues=(queue,))

	def test__Actor__format_queues_5(self):
		#queues as queue
		actor, queue = MockedActor(name="actor_name"), Queue(name="queue_name")
		queues = actor._Actor__format_queues(queues=queue)
		self.assertEquals(queues, [queue])

	def test__Actor__format_queues_6(self):
		#queues as random object
		actor, queue = MockedActor(name="actor_name"), "definitely_not_a_queue"
		with self.assertRaises(PypesException):
			queues = actor._Actor__format_queues(queues=queue)

	def test__Actor__format_queues_7(self):
		#queues as list with valid queue values
		actor, queue = MockedActor(name="actor_name"), Queue(name="queue_name")
		queues = actor._Actor__format_queues(queues=[queue])
		self.assertEquals(queues, [queue])

	def test__Actor__format_queues_8(self):
		#queues as list without valid queue values
		actor, queue = MockedActor(name="actor_name"), "definitely_not_a_queue"
		with self.assertRaises(PypesException):
			queues = actor._Actor__format_queues(queues=[queue])

	def test__Actor__format_queues_9(self):
		#queues as None
		actor, queue = MockedActor(name="actor_name"), None
		queues = actor._Actor__format_queues(queues=queue)
		self.assertEquals(queues, queue)