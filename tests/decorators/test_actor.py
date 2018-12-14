

import unittest
from pypes.actor import Actor
from pypes.decorators.actor import TimeTracker
from pypes.event import Event
from pypes.util.errors import ActorTimeout

class MockedActor(Actor):
	def consume(self, event, *args, **kwargs):
		return event, None
@TimeTracker
class MockedTrackerActor(Actor):
	def consume(self, event, *args, **kwargs):
		return event, None

class TestTimeTracker(unittest.TestCase):
	def test_TimeTracker_1(self):
		#test init
		actor = MockedActor(name="actor_name")
		self.assertEqual(getattr(actor, "new_event_timeout", None), None)
		actor = MockedTrackerActor(name="actor_name")
		self.assertEqual(getattr(actor, "new_event_timeout", None), 0)
		actor = MockedTrackerActor(name="actor_name", new_event_timeout=8)
		self.assertEqual(getattr(actor, "new_event_timeout", None), 8)

	def test_TimeTracker_2(self):
		#test wrapper
		actor, event = MockedActor(name="actor_name"), Event()
		self.assertEqual(event.get_started(actor_name=actor.name), None)
		self.assertEqual(event.get_ended(actor_name=actor.name), None)
		event, queues = actor._Actor__consume_wrapper(event=event, origin_queue=None)
		self.assertEqual(event.get_started(actor_name=actor.name), None)
		self.assertEqual(event.get_ended(actor_name=actor.name), None)
		actor, event = MockedTrackerActor(name="actor_name"), Event()
		self.assertEqual(event.get_started(actor_name=actor.name), None)
		self.assertEqual(event.get_ended(actor_name=actor.name), None)
		event, queues = actor._Actor__consume_wrapper(event=event, origin_queue=None)
		self.assertNotEqual(event.get_started(actor_name=actor.name), None)
		self.assertNotEqual(event.get_ended(actor_name=actor.name), None)
		self.assertNotEqual(event.get_started(actor_name=actor.name), event.get_ended(actor_name=actor.name))

	def test_TimeTracker_3(self):
		#test create event
		actor = MockedActor(name="actor_name")
		event1 = Event()
		event2 = actor.create_event()
		self.assertEqual(event1.timeout, None)
		self.assertEqual(event2.timeout, None)
		actor = MockedTrackerActor(name="actor_name", new_event_timeout=4)
		event1 = Event()
		event2 = actor.create_event()
		self.assertEqual(event1.timeout, None)
		self.assertEqual(event2.timeout, 4)

	def test_TimeTracker_4(self):
		#test timeout
		actor = MockedTrackerActor(name="actor_name", new_event_timeout=.1)
		event = actor.create_event()
		event, queues = actor._Actor__consume_wrapper(event=event, origin_queue=None)
		event.timeout_check()
		actor.sleep(.2)
		event, queues = actor._Actor__consume_wrapper(event=event, origin_queue=None)
		with self.assertRaises(ActorTimeout):
			event.timeout_check()


