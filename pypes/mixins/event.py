#!/usr/bin/env python

import xmltodict
import collections
import json
import re
import time
import logging

from lxml import etree
from decimal import Decimal
from xml.parsers import expat

from pypes.util.xpath import XPathLookup
from pypes.util.errors import InvalidEventConversion, ActorTimeout
from pypes import import_restriction
from pypes.globals.event import get_event_manager
from pypes.util.event import DefaultType, XMLType, JSONType, StringType
from pypes.util.async import timestamp
from pypes.globals.event import DEFAULT_LOG_FILENAME, DEFAULT_STATUS_CODE
from datetime import datetime

__all__ = []

if __name__.startswith(import_restriction):
    __all__ += [
        "EventFormatMixin",
        "XMLEventFormatMixin",
        "JSONEventFormatMixin",
        "StringEventFormatMixin",
        "TimingEventMixin",
        "LogEventMixin",
        "HttpEventMixin"
    ]

class EventFormatMixin:
    _format_type = DefaultType

class XMLEventFormatMixin(EventFormatMixin):
    _format_type = XMLType

class JSONEventFormatMixin(EventFormatMixin):
    _format_type = JSONType

class StringEventFormatMixin(EventFormatMixin):
    _format_type = StringType

class TimingEventMixin:

    def build_timing(self):
        self._timing = dict()

    #properties
    @property
    def elapsed(self):
        return self._timing.get("elapsed", None)

    @property
    def timeout(self):
        return self._timing.get("timeout", None)

    @timeout.setter
    def timeout(self, timeout):
        self._timing["timeout"] = timeout
    
    #internal funcs
    def __set_elapsed(self, timestamp):
        self._timing["elapsed"] = self.__calc_elapsed(start=self.created, end=timestamp)

    def __calc_elapsed(self, start=None, end=None):
        if not start is None and not end is None:
            return float(int((end - start) * 10000)) / float(10000)

    #getters and setters
    def get_elapsed(self, actor_name=None):
        if actor_name is None:
            return self.elapsed
        return self.__calc_elapsed(start=self.get_started(actor_name=actor_name), end=self.get_ended(actor_name=actor_name))

    def get_started(self, actor_name):
        return self._timing.get("actors", {}).get(actor_name, {}).get("started", None)
    
    def get_ended(self, actor_name):
        return self._timing.get("actors", {}).get(actor_name, {}).get("ended", None)
    
    def set_ended(self, actor_name, *args, **kwargs):
        timestamp = timestamp()
        self._timing["actors"] = self._timing.get("actors", {})
        actor_obj = self._timing["actors"].get(actor_name, {})
        actor_obj["ended"] = timestamp
        self._timing["actors"][actor_name] = actor_obj
        self.__set_elapsed(timestamp=timestamp)

    def set_started(self, actor_name, *args, **kwargs):
        timestamp = timestamp()
        self._timing["actors"] = self._timing.get("actors", {})
        actor_obj = self._timing["actors"].get(actor_name, {})
        actor_obj["started"] = timestamp
        self._timing["actors"][actor_name] = actor_obj
        self.__set_elapsed(timestamp=timestamp)

    #misc funcs
    def timeout_check(self, *args, **kwargs):
        timeout, elapsed = self.timeout, self.elapsed
        if not timeout is None and timeout <= elapsed and timeout > 0:
            raise ActorTimeout("Timeout exceeded: Processing took longer than expected")

class LogEventMixin:

    def build_logging(self, log_level=logging.DEBUG, log_origin_actor=None, log_filename=DEFAULT_LOG_FILENAME, message="", *args, **kwargs):
        self._logging = {"time": datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]}
        self.log_level = log_level
        self.log_origin_actor = log_origin_actor
        self.log_filename = log_filename
        self.log_message = log_message

    @property
    def log_level(self):
        return self._logging.get("level", None)

    @log_level.setter
    def log_level(self, level):
        self._logging.set("level", level if isinstance(level, (logging.CRITICAL, logging.ERROR, logging.WARN, logging.INFO)) else logging.DEBUG)

    @property
    def log_origin_actor(self):
        return self._logging.get("origin_actor", None)

    @log_origin_actor.setter
    def log_origin_actor(self, actor):
        self._logging.set("origin_actor", actor)

    @property
    def log_filename(self):
        return self._logging.get("filename", None)

    @log_filename.setter
    def log_filename(self, actor):
        self._logging.set("filename", actor)

    @property
    def log_message(self):
        return self._logging.get("message", None)

    @log_message.setter
    def log_message(self, actor):
        self._logging.set("message", actor)

    @property
    def log_time(self):
        return self._logging.get("time", None)
    
class HttpEventMixin:

    def build_environment(self, *args, **kwargs):
        self._environment = {
                "request": {
                    "headers": {},
                    "method": None,
                    "url":{
                        "scheme": None,
                        "domain": None,
                        "query": None,
                        "path": None,
                        "path_args": {},
                        "query_args": {}
                    }
                },
                "response": {
                    "headers": {},
                    "status": DEFAULT_STATUS_CODE
                },
                "remote": {
                    "address": None,
                    "port": None
                },
                "server": {
                    "name": None,
                    "port": None,
                    "protocol": None
                },
                "accepted_methods": []
            }

    @property
    def environment(self):
        return self._environment
    
    @property
    def request_headers(self):
        return self._environment.get("request", {}).get("headers", {})

    @request_headers.setter
    def request_headers(self, headers):
        self._environment["request"]["headers"] = headers

    @property
    def response_headers(self):
        return self._environment.get("response", {}).get("headers", {})

    @response_headers.setter
    def response_headers(self, headers):
        self._environment["response"]["headers"] = headers

    @property
    def status(self):
        return self._environment["response"]["status"]

    @status.setter
    def status(self, status):
        if status is None:
            status = DEFAULT_STATUS_CODE
        try:
            HTTPStatuses[status]
        except KeyError, AttributeError:
            raise InvalidEventModification("Unrecognized status code")
        else:
            self._environment["response"]["status"] = status

    def _set_error(self, exception):
        if exception is not None:
            error_state = HTTPStatusMap[exception.__class__]
            self.status = error_state.get("status", None)
            response_headers = self.response_headers
            response_headers.update(error_state.get("headers", {}))
            self.response_headers(headers=response_headers)
        super(BaseHttpEvent, self)._set_error(exception=exception)
