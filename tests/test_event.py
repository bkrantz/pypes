import unittest

#from compy.event import HttpEvent, Event
#from compy.errors import CompysitionException, ResourceNotFound
from pypes.event import *
class TestEvent(unittest.TestCase):
    def test_init(self):
        Event()