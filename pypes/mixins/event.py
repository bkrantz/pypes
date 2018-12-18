#!/usr/bin/env python

import xmltodict
import collections
import json
import re
import time

from lxml import etree
from decimal import Decimal
from xml.parsers import expat

from pypes.util.xpath import XPathLookup
from pypes.util.errors import InvalidEventConversion, ActorTimeout
from pypes import import_restriction
from pypes.globals.event import get_conversion_method_manager

__all__ = []

if __name__.startswith(import_restriction):
    __all__ += [
        "EventFormatMixin",
        "XMLEventFormatMixin",
        "JSONEventFormatMixin",
        "EventTimingMixin"
    ]

class EventConversionMixin:

    conversion_methods = get_conversion_method_manager().get_conversion_methods()

    def isInstance(self, convert_to, current_event=None):
        if current_event is None:
            current_event = self
        return convert_to in current_event.conversion_parents or convert_to == current_event.__class__

    def convert(self, convert_to, current_event=None, force=False, ignore_data=False):
        if current_event is None:
            current_event = self
        try:
            if not force and self.isInstance(convert_to=convert_to, current_event=current_event):
                return current_event
            new_class = convert_to.__new__(convert_to)
            new_class.__dict__.update(current_event.__dict__)
            if not ignore_data:
                new_class.data = current_event.data
        except Exception as err:
            raise InvalidEventConversion("Unable to convert event. <Attempted {old} -> {new}>".format(old=current_event.__class__, new=convert_to))
        return new_class

class XMLEventConversionMixin(EventConversionMixin):
    conversion_methods = get_conversion_method_manager().get_conversion_methods("XML")

class JSONEventConversionMixin(EventConversionMixin):
    conversion_methods = get_conversion_method_manager().get_conversion_methods("JSON")

class EventFormatMixin(EventConversionMixin):
    
    def _get_state(self):
        return dict(self.__dict__)

    def format_error(self):
        if self.error:
            messages = self.error.message
            if not isinstance(messages, list):
                messages = [messages]
            errors = map(lambda _error: dict(message=str(getattr(_error, "message", _error)), **self.error.__dict__), messages)
            return errors
        else:
            return None

    def error_string(self):
        if self.error:
            return str(self.format_error())
        else:
            return None

    def data_string(self):
        return str(self.data)

class XMLEventFormatMixin(XMLEventConversionMixin, EventFormatMixin):

    def _get_state(self):
        state = EventFormatMixin._get_state(self)
        if self.data is not None:
            state['_data'] = etree.tostring(self.data)
        return state

    def data_string(self):
        try:
            return etree.tostring(self.data)
        except TypeError:
            return None

    def format_error(self):
        errors = EventFormatMixin.format_error(self)
        if errors is not None and len(errors) > 0:
            result = etree.Element("errors")
            for error in errors:
                error_element = etree.Element("error")
                message_element = etree.Element("message")
                error_element.append(message_element)
                message_element.text = error['message']
                result.append(error_element)
        return result

    def error_string(self):
        error = self.format_error()
        if error is not None:
            error = etree.tostring(error, pretty_print=True)
        return error

class JSONEventFormatMixin(JSONEventConversionMixin, EventFormatMixin):

    def _get_state(self):
        state = EventFormatMixin._get_state(self)
        if self.data is not None:
            state['_data'] = json.dumps(self.data)
        return state

    def data_string(self):
        return json.dumps(self.data, default=get_conversion_method_manager().decimal_default)

    def error_string(self):
        error = self.format_error()
        if error:
            try:
                error = json.dumps({"errors": error})
            except Exception:
                pass
        return error

class EventTimingMixin:
    def _timing_init(self, *args, **kwargs):
        self.__timing = {}
        self.created = self.__get_timestamp()

    #properties
    @property
    def elapsed(self):
        return self.__timing.get("elapsed", None)

    @property
    def timeout(self):
        return self.__timing.get("timeout", None)

    @timeout.setter
    def timeout(self, timeout):
        self.__timing["timeout"] = timeout
    
    @property
    def created(self):
        return self.__timing.get("created", None)

    @created.setter
    def created(self, timestamp):
        if not self.created is None:
            raise InvalidEventModification("Cannot alter created timestamp once it has been set.")
        else:
            self.__timing["created"] = timestamp

    #internal funcs
    def __set_elapsed(self, timestamp):
        self.__timing["elapsed"] = self.__calc_elapsed(start=self.created, end=timestamp)

    def __get_timestamp(self,):
        return time.time()

    def __calc_elapsed(self, start=None, end=None):
        if not start is None and not end is None:
            return float(int((end - start) * 10000)) / float(10000)

    #getters and setters
    def get_elapsed(self, actor_name=None):
        if actor_name is None:
            return self.elapsed
        return self.__calc_elapsed(start=self.get_started(actor_name=actor_name), end=self.get_ended(actor_name=actor_name))

    def get_started(self, actor_name):
        return self.__timing.get("actors", {}).get(actor_name, {}).get("started", None)
    
    def set_started(self, actor_name):
        timestamp = self.__get_timestamp()
        self.__timing["actors"] = self.__timing.get("actors", {})
        actor_obj = self.__timing["actors"].get(actor_name, {})
        actor_obj["started"] = timestamp
        self.__timing["actors"][actor_name] = actor_obj
        self.__set_elapsed(timestamp=timestamp)

    def get_ended(self, actor_name):
        return self.__timing.get("actors", {}).get(actor_name, {}).get("ended", None)
    
    def set_ended(self, actor_name):
        timestamp = self.__get_timestamp()
        self.__timing["actors"] = self.__timing.get("actors", {})
        actor_obj = self.__timing["actors"].get(actor_name, {})
        actor_obj["ended"] = timestamp
        self.__timing["actors"][actor_name] = actor_obj
        self.__set_elapsed(timestamp=timestamp)

    #misc funcs
    def timeout_check(self,):
        timeout, elapsed = self.timeout, self.elapsed
        if not timeout is None and timeout <= elapsed and timeout > 0:
            raise ActorTimeout("Timeout exceeded: Processing took longer than expected")
