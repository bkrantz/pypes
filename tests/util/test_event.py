
from pypes.testutils import BaseUnitTest
from pypes.util.errors import (PypesException, QueueEmpty, QueueFull, QueueConnected, SetupError, ReservedName, ActorInitFailure, InvalidEventConversion, InvalidEventDataModification, InvalidEventModification, InvalidActorOutput, InvalidActorInput, ResourceNotModified, MalformedEventData, UnauthorizedEvent, ForbiddenEvent, ResourceNotFound, EventCommandNotAllowed, ActorTimeout, ResourceConflict, ResourceGone, UnprocessableEventData, EventRateExceeded, ServiceUnavailable, EventAttributeError)
from pypes.event import *
class TestConversionMethods(BaseUnitTest):
	
    def test_PypesException(self):
    	exception = PypesException(message="u did something wrong", func="a random kwarg")
    	self.assertEqual(exception.message, ["u did something wrong"])
    	self.assertEqual(exception.func, "a random kwarg")