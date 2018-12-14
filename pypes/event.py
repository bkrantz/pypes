#!/usr/bin/env python

import traceback
import collections
from uuid import uuid4 as uuid
from copy import deepcopy
from datetime import datetime

from __init__ import import_restriction
from pypes.util.errors import (InvalidEventDataModification, InvalidEventModification)
from pypes.mixins.event import (EventFormatMixin, XMLEventFormatMixin, JSONEventFormatMixin, EventTimingMixin)
from pypes.globals.event import DEFAULT_STATUS_CODE, DEFAULT_SERVICE, HTTPStatuses, HTTPStatusMap

__all__ = []

if __name__.startswith(import_restriction):
    __all__ += [
        "BaseEvent",
        "Event",
        "LogEvent",
        "HttpEvent",
        "XMLEvent",
        "XMLHttpEvent",
        "JSONEvent",
        "JSONHttpEvent",
    ]

class BaseEvent(object):

    def __init__(self, meta_id=None, data=None, service=None, *args, **kwargs):
        self.service = service
        self.event_id = uuid().get_hex()
        self.meta_id = meta_id if meta_id else self.event_id
        self._data = None
        self.data = data
        self.error = None
        self._timing_init()
        self.__dict__.update(kwargs)
        self._splits = list()

    def get_splits(self):
        return self._splits

    def add_split(self, key):
        self._splits.append(key)

    def set(self, key, value):
        try:
            setattr(self, key, value)
            return True
        except Exception:
            return False

    def get(self, key, default=None):
        return getattr(self, key, default)

    @property
    def service(self):
        return self._service

    @service.setter
    def service(self, service):
        self._set_service(service)

    def _set_service(self, service):
        self._service = service
        if self._service == None:
            self._service = DEFAULT_SERVICE

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        try:
            self._data = self.conversion_methods[data.__class__](data)
        except KeyError:
            raise InvalidEventDataModification("Data of type '{_type}' was not valid for event type {cls}: {err}".format(_type=type(data), cls=self.__class__, err=traceback.format_exc()))
        except ValueError as err:
            raise InvalidEventDataModification("Malformed data: {err}".format(err=err))
        except Exception as err:
            raise InvalidEventDataModification("Unknown error occurred on modification: {err}".format(err=err))

    @property
    def event_id(self):
        return self._event_id

    @event_id.setter
    def event_id(self, event_id):
        if self.get("_event_id", None) is not None:
            raise InvalidEventDataModification("Cannot alter event_id once it has been set. A new event must be created")
        else:
            self._event_id = event_id

    def get_properties(self):
        return {k: v for k, v in self.__dict__.iteritems() if k != "data" and k != "_data"}

    def __getstate__(self):
        return self._get_state()

    def __setstate__(self, state):
        self.__dict__ = state
        self.data = state.get('_data', None)
        self.error = state.get('_error', None)

    def __str__(self):
        return str(self.__getstate__())

    @property
    def error(self):
        return self._error

    @error.setter
    def error(self, exception):
        self._set_error(exception)

    def _set_error(self, exception):
        self._error = exception

    def clone(self):
        return deepcopy(self)

class BaseLogEvent(BaseEvent):
    def __init__(self, level, origin_actor, message, id=None, *args, **kwargs):
        super(BaseLogEvent, self).__init__(*args, **kwargs)
        self.id = id
        self.level = level
        self.time = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
        self.origin_actor = origin_actor
        self.message = message
        self.data = {
            "id":              self.id,
            "level":            self.level,
            "time":             self.time,
            "origin_actor":     self.origin_actor,
            "message":          self.message
        }

class BaseHttpEvent(BaseEvent):
    def __init__(self, environment={}, *args, **kwargs):
        self._ensure_environment(environment)
        super(BaseHttpEvent, self).__init__(*args, **kwargs)

    def __recursive_update(self, d, u):
        for k, v in u.iteritems():
            if isinstance(v, collections.Mapping):
                d[k] = self.__recursive_update(d.get(k, {}), v)
            else:
                d[k] = v
        return d

    def _set_service(self, service):
        if service is None:
            service = self.environment["request"]["url"]["path_args"].get("queue", None)
        super(BaseHttpEvent, self)._set_service(service=service)

    def _ensure_environment(self, environment):
        if self.get("environment", None) is None:
            self.environment = {
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
        self.environment = self.__recursive_update(self.environment, environment)

    @property
    def status(self):
        return self.environment["response"]["status"]

    @status.setter
    def status(self, status):
        if status is None:
            status = DEFAULT_STATUS_CODE
        try:
            HTTPStatuses[status]
        except KeyError, AttributeError:
            raise InvalidEventModification("Unrecognized status code")
        else:
            self.environment["response"]["status"] = status

    def update_headers(self, headers={}, **kwargs):
        self.environment["response"]["headers"].update(headers)
        self.environment["response"]["headers"].update(kwargs)

    def _set_error(self, exception):
        if exception is not None:
            error_state = HTTPStatusMap[exception.__class__]
            self.status = error_state.get("status", None)
            self.update_headers(headers=error_state.get("headers", {}))
        super(BaseHttpEvent, self)._set_error(exception)

class Event(EventFormatMixin, EventTimingMixin, BaseEvent):
    conversion_parents = []

class LogEvent(EventFormatMixin, EventTimingMixin, BaseLogEvent):
    conversion_parents = [Event]

class HttpEvent(EventFormatMixin, EventTimingMixin, BaseHttpEvent):
    conversion_parents = [Event]

class XMLEvent(XMLEventFormatMixin, EventTimingMixin, BaseEvent):
    conversion_parents = [Event]

class XMLHttpEvent(XMLEventFormatMixin, EventTimingMixin, BaseHttpEvent):
    conversion_parents = [Event, HttpEvent]

class JSONEvent(JSONEventFormatMixin, EventTimingMixin, BaseEvent):
    conversion_parents = [Event]

class JSONHttpEvent(JSONEventFormatMixin, EventTimingMixin, BaseHttpEvent):
    conversion_parents = [Event, HttpEvent]
