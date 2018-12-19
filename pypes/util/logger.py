#!/usr/bin/env python

import logging

from pypes.util.queue import InternalQueuePool
from pypes.event import LogEvent
from pypes.util.errors import QueueFull
from pypes import import_restriction

__all__ = []

if __name__.startswith(import_restriction):
    __all__ += [
        "Logger"
    ]

class Logger(object):

    """**Generates Compysition formatted log messages following the python priority definition to a pool of queues**

    We use a pool in order to support multiple logging types per process. For example, sending to a third party log
    aggregator as WELL as using a filelogger

    Args:
        - name(str):
            | The name to use when sending log events
        - queue_pool(InternalQueuePool):
            | The pool to use when sending log events
    """

    def __init__(self, name, queue_pool):
        self.name = name
        if not isinstance(queue_pool, InternalQueuePool):
            raise TypeError("Logger queue_pool must be of type 'InternalQueuePool'")

        self.__pool = queue_pool

    def log(self, level, message, event=None, log_entry_id=None):
        """
        Uses log_entry_id explicitely as the logged ID, if defined. Otherwise, will attempt to ascertain the ID from 'event', if passed
        """
        if not log_entry_id:
            if event:
                log_entry_id = event.meta_id

        for key in self.__pool.iterkeys():
            try:
                log_event = LogEvent(log_level=level, log_origin_actor=self.name, log_message=message)
                self.__pool[key].put(log_event)
            except QueueFull:
                self.__pool.wait_until_free()
                self.__pool[key].put(log_event)

    def critical(self, message, event=None, log_entry_id=None):
        """Generates a log message with priority logging.CRITICAL
        """
        self.log(logging.CRITICAL, message, event=event, log_entry_id=log_entry_id)

    def error(self, message, event=None, log_entry_id=None):
        """Generates a log message with priority error(3).
        """
        self.log(logging.ERROR, message, event=event, log_entry_id=log_entry_id)

    def warn(self, message, event=None, log_entry_id=None):
        """Generates a log message with priority logging.WARN
        """
        self.log(logging.WARN, message, event=event, log_entry_id=log_entry_id)
    warning=warn

    def info(self, message, event=None, log_entry_id=None):
        """Generates a log message with priority logging.INFO.
        """
        self.log(logging.INFO, message, event=event, log_entry_id=log_entry_id)

    def debug(self, message, event=None, log_entry_id=None):
        """Generates a log message with priority logging.DEBUG
        """
        self.log(logging.DEBUG, message, event=event, log_entry_id=log_entry_id)