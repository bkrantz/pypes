
from pypes.testutils import BaseUnitTest
from pypes.util.errors import (PypesException, QueueEmpty, QueueFull, QueueConnected, SetupError, ReservedName, ActorInitFailure, InvalidEventConversion, InvalidEventDataModification, InvalidEventModification, InvalidActorOutput, InvalidActorInput, ResourceNotModified, MalformedEventData, UnauthorizedEvent, ForbiddenEvent, ResourceNotFound, EventCommandNotAllowed, ActorTimeout, ResourceConflict, ResourceGone, UnprocessableEventData, EventRateExceeded, ServiceUnavailable, EventAttributeError)

class TestPypesException(BaseUnitTest):
    def test_PypesException(self):
    	exception = PypesException(message="u did something wrong", func="a random kwarg")
    	self.assertEqual(exception.message, ["u did something wrong"])
    	self.assertEqual(exception.func, "a random kwarg")
    def test_QueueEmpty(self):
    	self.assertEqual(issubclass(QueueEmpty, PypesException), True)
    def test_QueueFull(self):
    	self.assertEqual(issubclass(QueueFull, PypesException), True)
    def test_QueueConnected(self):
    	self.assertEqual(issubclass(QueueConnected, PypesException), True)
    def test_SetupError(self):
    	self.assertEqual(issubclass(SetupError, PypesException), True)
    def test_ReservedName(self):
    	self.assertEqual(issubclass(ReservedName, PypesException), True)
    def test_ActorInitFailure(self):
    	self.assertEqual(issubclass(ActorInitFailure, PypesException), True)
    def test_InvalidEventConversion(self):
    	self.assertEqual(issubclass(InvalidEventConversion, PypesException), True)
    def test_InvalidEventDataModification(self):
    	self.assertEqual(issubclass(InvalidEventDataModification, PypesException), True)
    def test_InvalidEventModification(self):
    	self.assertEqual(issubclass(InvalidEventModification, PypesException), True)
    def test_InvalidActorOutput(self):
    	self.assertEqual(issubclass(InvalidActorOutput, PypesException), True)
    def test_InvalidActorInput(self):
    	self.assertEqual(issubclass(InvalidActorInput, PypesException), True)
    def test_ResourceNotModified(self):
    	self.assertEqual(issubclass(ResourceNotModified, PypesException), True)
    def test_MalformedEventData(self):
    	self.assertEqual(issubclass(MalformedEventData, PypesException), True)
    def test_UnauthorizedEvent(self):
    	self.assertEqual(issubclass(UnauthorizedEvent, PypesException), True)
    def test_ForbiddenEvent(self):
    	self.assertEqual(issubclass(ForbiddenEvent, PypesException), True)
    def test_ResourceNotFound(self):
    	self.assertEqual(issubclass(ResourceNotFound, PypesException), True)
    def test_EventCommandNotAllowed(self):
    	self.assertEqual(issubclass(EventCommandNotAllowed, PypesException), True)
    def test_ActorTimeout(self):
    	self.assertEqual(issubclass(ActorTimeout, PypesException), True)
    def test_ResourceConflict(self):
    	self.assertEqual(issubclass(ResourceConflict, PypesException), True)
    def test_ResourceGone(self):
    	self.assertEqual(issubclass(ResourceGone, PypesException), True)
    def test_UnprocessableEventData(self):
    	self.assertEqual(issubclass(UnprocessableEventData, PypesException), True)
    def test_EventRateExceeded(self):
    	self.assertEqual(issubclass(EventRateExceeded, PypesException), True)
    def test_ServiceUnavailable(self):
    	self.assertEqual(issubclass(ServiceUnavailable, PypesException), True)
    def test_EventAttributeError(self):
    	self.assertEqual(issubclass(EventAttributeError, PypesException), True)
