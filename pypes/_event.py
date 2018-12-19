import logging


#event data type definitions
class JSONType: pass
class XMLType: pass
class StringType: pass
class DefaultType: pass

class EventFormatMixin:
    _format_type = DefaultType

class XMLEventFormatMixin(EventFormatMixin):
    _format_type = XMLType

class JSONEventFormatMixin(EventFormatMixin):
    _format_type = JSONType

class StringEventFormatMixin(EventFormatMixin):
    _format_type = StringType

class EventManager:
    __XML_TYPES = [etree._Element, etree._ElementTree, etree._XSLTResultTree]
    __JSON_TYPES = [dict, list, collections.OrderedDict]

    __pypes_xml_wrapper_key = "pypes_conversion_wrapper"
    __pypes_json_type_key = "@pypes_json_type"

    __xml_conversion_methods = {str: lambda data: etree.fromstring(data)}
    __xml_conversion_methods.update(dict.fromkeys(EventManager.__XML_TYPES, lambda data: data))
    __xml_conversion_methods.update(dict.fromkeys(EventManager.__JSON_TYPES, lambda data: etree.fromstring(xmltodict.unparse(self.__internal_xmlify(data)).encode('utf-8'))))
    __xml_conversion_methods.update({None.__class__: lambda data: etree.fromstring("<%s/>" % EventManager.__pypes_xml_wrapper_key)})
    __json_conversion_methods = {str: lambda data: json.loads(data)}
    __json_conversion_methods.update(dict.fromkeys(EventManager.__JSON_TYPES, lambda data: json.loads(json.dumps(data, default=self.__decimal_default))))
    __json_conversion_methods.update(dict.fromkeys(EventManager.__XML_TYPES, lambda data: self.__remove_internal_xmlify(xmltodict.parse(etree.tostring(data), expat=expat))))
    __json_conversion_methods.update({None.__class__: lambda data: {}})
    __string_conversion_methods = {str: lambda data: data}
    __string_conversion_methods.update(dict.fromkeys(EventManager.__JSON_TYPES, lambda data: json.dumps(data, default=self.__decimal_default)))
    __string_conversion_methods.update(dict.fromkeys(EventManager.__XML_TYPES, lambda data: etree.tostring(data)))
    __string_conversion_methods.update({None.__class__: lambda data: ""})
    __default_conversion_methods = collections.defaultdict(lambda: lambda data: data)

    convert_to_xml = lambda value: EventManager.__xml_conversion_methods[value.__class__](data=value)
    convert_to_json = lambda value: EventManager.__json_conversion_methods[value.__class__](data=value)
    convert_to_string = lambda value: EventManager.__string_conversion_methods[value.__class__](data=value)
    convert_to_default = lambda value: EventManager.__default_conversion_methods[value.__class__](data=value)

    __conversion_types = {
        JSONType: EventManager.convert_to_json,
        XMLType: EventManager.convert_to_xml,
        StringType: EventManager.convert_to_string
        DefaultType: EventManager.convert_to_default
    }

    def is_xml_type(self, clazz):
        return clazz in EventManager.__XML_TYPES

    def format_error(self, event):
        if not event.error is None:
            messages = [{"message": message} for message in event.error.message]
            obj = {"errors":{"error": messages}}
            return self.ensure_formating(event=event, new_value=obj)
        return None

    def stringify(self, new_value):
        self.convert_to_string(value=new_value)

    def ensure_formating(self, event, new_value):
        try:
            return EventManager.__conversion_types[event._format_type](value=new_value)
        except KeyError:
            raise InvalidEventDataModification("Data of type '{_type}' was not valid for event type {cls}: {err}".format(_type=type(data), cls=self.__class__, err=traceback.format_exc()))
        except ValueError as err:
            raise InvalidEventDataModification("Malformed data: {err}".format(err=err))
        except Exception as err:
            raise InvalidEventDataModification("Unknown error occurred on modification: {err}".format(err=err))

	def convert(self, event, convert_to):
		if not self.is_instance(event=event, convert_to=convert_to):
            try:
                new_event = convert_to.__new__(cls=convert_to)
                new_event.__dict__.update(event.__dict__)
                new_event.data = event.data
            except Exception:
                raise InvalidEventConversion("Unable to convert event. <Attempted {old} -> {new}>".format(old=event.__class__, new=convert_to))
            else:
                return new_event
        return event

	def is_instance(self, event, convert_to):
        for base in convert_to.__bases__:
            if not issubclass(event.__class__, base):
                return False
        return True

    def __internal_xmlify(self, _json):
        if isinstance(_json, dict) and len(_json) == 0:
            _json = {self.__compy_wrapper_key: {}}
        if isinstance(_json, list) or len(_json) > 1:
            _json = {self.__compy_wrapper_key: _json}
        _, value = next(iter(_json.items()))
        if isinstance(value, list):
            _json = {self.__compy_wrapper_key: _json}
        return _json

    def __remove_internal_xmlify(self, _json):
        if len(_json) == 1 and isinstance(_json, dict):
            key, value = next(iter(_json.items()))
            if key == self.__compy_wrapper_key:
                _json = value
        self.__json_conversion_crawl(_json)
        return _json

    def __json_get_value_of_dict(self, dict_obj):
        text = dict_obj.get(EventManager.__xml_to_json_attr_key, None)
        if text is None or len(dict_obj) > 1:
            return dict_obj
        else:
            return text

    def __json_conversion_crawl_nested(self, _json):
        if isinstance(_json, dict):
            for key, value in _json.items():
                _json[key] = self.__json_conversion_crawl_nested(_json=value)
            json_type = _json.pop(self.__compy_json_type_key, None)
            if json_type == "list":
                new_obj = self.__json_get_value_of_dict(dict_obj=_json)
                if new_obj is None or (isinstance(new_obj, dict) and len(new_obj) == 0):
                    return []
                return [new_obj]
            elif json_type == "string":
                new_value = self.__json_get_value_of_dict(dict_obj=value)
                if isinstance(new_value, (dict, list)):
                    return json.dumps(new_value)
                else:
                    return new_value
            elif json_type == "dict":
                return _json
            elif json_type is not None:
                return None
            return _json
        elif isinstance(_json, list):
            for index, value in enumerate(_json):
                if isinstance(value, dict):
                    for key, sub_value in value.items():
                        value[key] = self.__json_conversion_crawl_nested(_json=sub_value)
                    json_type = value.pop(self.__compy_json_type_key, None)
                    if json_type == "list":
                        _json[index] = self.__json_get_value_of_dict(dict_obj=value)
                    elif json_type == "string":
                        new_value = self.__json_get_value_of_dict(dict_obj=value)
                        if isinstance(new_value, (dict, list)):
                            _json[index] = json.dumps(new_value)
                        else:
                            _json[index] = new_value
                    elif json_type == "dict":
                        _json[index] = None
                    else:
                        _json[index] = value
                else:
                    _json[index] = self.__json_conversion_crawl_nested(_json=value)
        return _json

    def __json_conversion_crawl(self, _json):
        if isinstance(_json, dict):
            for key, value in _json.items():
                _json[key] = self.__json_conversion_crawl_nested(_json=value)
        return _json

    def __decimal_default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError

    def get_timestamp(self):
        return time.time()

class BaseEvent(object):
	_build_hooks = []
	_pre_consume_hooks = []
	_post_consume_hooks = []
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

	def __process_hooks(self, hooks, cascade=False, *args, **kwargs):
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
        self._data = get_event_formatter().ensure_formating(event=self, new_value=data)

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
        return get_event_formatter().format_error(event=self)

    @property
    def data_string(self):
        return get_event_formatter().stringify(new_value=self._data)

    def __getstate__(self):
        pickle_dict = dict(self.__dict__)
        pickled_xml_attrs = []
        for key, value in pickle_dict:
            if get_event_formatter().is_xml_type(clazz=value.__class__):
                pickled_xml_attrs.append(key)
                pickle_dict[key] = get_event_formatter().convert_to_string(value=value)
        pickle_dict[BaseEvent.__pickled_xml_attr] = pickled_xml_attrs
        return pickle_dict

    def __setstate__(self, state):
        pickled_xml_attrs = pickle_dict[BaseEvent.__pickled_xml_attr]
        del pickle_dict[BaseEvent.__pickled_xml_attr]
        for key in pickled_xml_attrs:
            pickle_dict[key] = get_event_formatter().convert_to_xml(value=pickle_dict[key])
        self.__dict__ = state

    def __str__(self):
        return str(self.__getstate__())

    def clone(self):
        return deepcopy(self)

def TimingEventMixin:

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

    def build_logging(self, *args, **kwargs):
        self._logging = {
            "level": logging.DEBUG,
            "origin_actor": None,
            "filename": DEFAULT_LOG_FILENAME,
            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3],
            "message": ""
        }

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

__event_mixin_hooks = collections.defaultdict(lambda: {},
    {
        TimingEventMixin: {
            "_build_hooks" = ["build_timing"]
            "_pre_consume_hooks" = ["set_started", "timeout_check"]
            "_post_consume_hooks" = ["set_ended", "timeout_check"]
        },
        LogEventMixin: {
            "_build_hooks" = ["build_logging"]
        },
        HttpEventMixin: {
            "_build_hooks" = ["build_environment"]
        }
    }
)

__data_format_mixins = {
    EventFormatMixin: "Default",
    XMLEventFormatMixin: "XML",
    JSONEventFormatMixin: "JSON",
    StringEventFormatMixin: "String"
}

__universal_mixins = [
    TimingEventMixin: "Timing",
    LogEventMixin: "Log",
    HttpEventMixin: "Http"
]

__all__ = []
for data_mixin, descriptor in __data_format_mixins.iteritems():
    # for each permutation of universal mixins
    for comb_length in xrange(0, len(stuff)+1):
        for subset in itertools.permutations(stuff, comb_length):
            class_name = descriptor
            current_build_hooks, current_pre_consume_hooks, current_post_consume_hooks = [], [], []
            for mixin in subset:
                class_name += __universal_mixins[mixin]
                current_build_hooks.extend(__event_mixin_hooks[mixin].get("_build_hooks", []))
                current_pre_consume_hooks.extend(__event_mixin_hooks[mixin].get("_pre_consume_hooks", []))
                current_post_consume_hooks.extend(__event_mixin_hooks[mixin].get("_post_consume_hooks", []))
            class_name += "Event"
            parent_classes = (data_mixin,) + subset + (BaseEvent,)

            __all__.append(
                type(
                    class_name, 
                    parent_classes, 
                    {
                        "_build_hooks": current_build_hooks,
                        "_pre_consume_hooks": current_pre_consume_hooks,
                        "_post_consume_hooks": current_post_consume_hooks,
                    })
                )
print __all__



'''
class Event(EventFormatMixin, BaseEvent):
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
'''