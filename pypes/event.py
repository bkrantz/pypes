import logging
import collections
import itertools
from pypes.mixins.event import EventFormatMixin, XMLEventFormatMixin, JSONEventFormatMixin, StringEventFormatMixin, TimingEventMixin, LogEventMixin, HttpEventMixin
from uuid import uuid4 as uuid
from pypes.util.async import timestamp
from pypes.util import ignored
from copy import deepcopy
from pypes.globals.event import get_event_manager
from pypes.util.errors import PypesException

class BaseEvent(object):
    __pickled_xml_attr = "pickled_xml_attrs"

    def __init__(self, data=None, service=None, *args, **kwargs):
        self._service = service
        self._event_id = uuid().get_hex()
        self._data = data
        self._error = None
        self.splits = list()
        self._created = timestamp()
        self.__dict__.update(kwargs)

    def __new__(cls, *args, **kwargs):
        instance = super(BaseEvent, cls).__new__(cls)
        instance.build(*args, **kwargs)
        return instance

    def build(self, *args, **kwargs):
        self.__process_hooks(hooks=self._build_hooks, *args, **kwargs)

    def __process_hooks(self, hooks=[], cascade=False, *args, **kwargs):
        for hook in hooks:
            with ignored(AttributeError):
                getattr(self, hook)(*args, **kwargs)

    def pre_consume_hooks(self, *args, **kwargs):
        self.__process_hooks(hooks=self._pre_consume_hooks, *args, **kwargs)

    def post_consume_hooks(self, *args, **kwargs):
        self.__process_hooks(hooks=self._post_consume_hooks, *args, **kwargs)

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
        self._service = DEFAULT_SERVICE if service is None else service

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self._data = get_event_manager().ensure_formating(event=self, new_value=data)

    @property
    def created(self):
        return self._created

    @created.setter
    def created(self, timestamp):
        if not self._created is None:
            raise InvalidEventModification(message="Cannot alter created timestamp once it has been set.")
        else:
            self._created = timestamp

    @property
    def event_id(self):
        return self._event_id

    @event_id.setter
    def event_id(self, id):
        if not self._event_id is None:
            raise InvalidEventModification(message="Cannot alter event_id once it has been set.")
        else:
            self._event_id = id

    @property
    def error(self):
        return self._error

    @error.setter
    def error(self, exception):
        self._set_error(exception=exception)

    def _set_error(self, exception):
        self._error = exception if isinstance(exception, PypesException) else PypesException(message="Internal Error")

    @property
    def format_error(self):
        return get_event_manager().format_error(event=self)

    @property
    def data_string(self):
        return get_event_manager().stringify(new_value=self._data)

    def __getstate__(self):
        pickle_dict = dict(self.__dict__)
        pickled_xml_attrs = []
        for key, value in pickle_dict.iteritems():
            if get_event_manager().is_xml_type(clazz=value.__class__):
                pickled_xml_attrs.append(key)
                pickle_dict[key] = get_event_manager().convert_to_string(value=value)
        pickle_dict[BaseEvent.__pickled_xml_attr] = pickled_xml_attrs
        return pickle_dict

    def __setstate__(self, state):
        pickled_xml_attrs = state[BaseEvent.__pickled_xml_attr]
        del state[BaseEvent.__pickled_xml_attr]
        for key in pickled_xml_attrs:
            state[key] = get_event_manager().convert_to_xml(value=state[key])
        self.__dict__ = state

    def __str__(self):
        return str(self.__getstate__())

    def clone(self):
        return deepcopy(self)

__event_mixin_hooks = collections.defaultdict(lambda: {},
    {
        TimingEventMixin: {
            "_build_hooks": ["build_timing"],
            "_pre_consume_hooks": ["set_started", "timeout_check"],
            "_post_consume_hooks": ["set_ended", "timeout_check"]
        },
        LogEventMixin: {
            "_build_hooks": ["build_logging"]
        },
        HttpEventMixin: {
            "_build_hooks": ["build_environment"]
        }
    }
)

__data_format_mixins = {
    EventFormatMixin: "",
    XMLEventFormatMixin: "XML",
    JSONEventFormatMixin: "JSON",
    StringEventFormatMixin: "String"
}

__universal_mixins = {
    HttpEventMixin: "Http",
    TimingEventMixin: "Timing",
    LogEventMixin: "Log"
}

__all__ = []

def build_class_name(data_mixin, universal_mixins):
    class_name = __data_format_mixins[data_mixin]
    for mixin in universal_mixins:
        class_name += __universal_mixins[mixin]
    return class_name + "Event"

def build_hook_lists(mixins):
    build, pre, post = [], [], []
    for mixin in mixins:
        build.extend(__event_mixin_hooks[mixin].get("_build_hooks", []))
        pre.extend(__event_mixin_hooks[mixin].get("_pre_consume_hooks", []))
        post.extend(__event_mixin_hooks[mixin].get("_post_consume_hooks", []))
    return build, pre, post

for data_mixin, descriptor in __data_format_mixins.iteritems():
    # for each combination of universal mixins
    for comb_length in xrange(0, len(__universal_mixins)+1):
        for subset in itertools.combinations(__universal_mixins, comb_length):
            class_name = build_class_name(data_mixin=data_mixin, universal_mixins=subset)
            build, pre, post = build_hook_lists(mixins=(data_mixin,)+subset)
            parent_classes = (data_mixin,) + subset + (BaseEvent,)
            current_class = type(
                class_name, 
                parent_classes, 
                {
                    "_build_hooks": build,
                    "_pre_consume_hooks": pre,
                    "_post_consume_hooks": post,
                })
            globals()[class_name] = current_class
            __all__.append(class_name)

'''
EVENT TYPES

################

Event
HttpEvent
HttpTimingEvent
HttpLogEvent
TimingEvent
TimingLogEvent
LogEvent
XMLEvent
XMLHttpEvent
XMLHttpTimingEvent
XMLHttpLogEvent
XMLTimingEvent
XMLTimingLogEvent
XMLLogEvent
JSONEvent
JSONHttpEvent
JSONHttpTimingEvent
JSONHttpLogEvent
JSONTimingEvent
JSONTimingLogEvent
JSONLogEvent
StringEvent
StringHttpEvent
StringHttpTimingEvent
StringHttpLogEvent
StringTimingEvent
StringTimingLogEvent
StringLogEvent
'''