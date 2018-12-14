#!/usr/bin/env python
'''
from .actor import Actor
from .queue import Queue
from .queue import QueuePool
from .logger import Logger
from .director import Director
from .event import Event
'''
from gevent import monkey

monkey.patch_all()

__version__ = '0.1.2'
version = __version__

import_restriction = "pypes."

__all__ = [
	"version",
	"import_restriction"
]