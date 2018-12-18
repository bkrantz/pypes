
class EventFormatter:
	def convert(self, event, target_event_class):
		pass

	def convert_data(self, event):
		pass

	def is_instance(self, event, event_class):
		pass

__event_formatter = None

def get_event_formatter():
	global __event_formatter
	if __event_formatter is None:
		__event_formatter = EventFormatter()
	return __event_formatter

class BaseEvent(object):
	_init_hooks = []
	_pre_consume_hooks = []
	_post_consume_hooks = []

	def __init__(self, data=None, service=None, *args, **kwargs):
		self._service = service
		self._event_id = uuid().get_hex()
		self._data = data
		self._error = None
		self.splits = list()
		self._created = self.__get_timestamp()
		args, kwargs = self.__process_hooks(hooks=self._init_hooks, cascade=True, *args, **kwargs)
		self.__dict__.update(kwargs)

	def __process_hooks(self, hooks, cascade=False, *args, **kwargs):
		for hook in hooks:
			with ignored(AttributeError):
				returns = getattr(self, hook)(*args, **kwargs)
				args, kwargs = returns if cascade else (args, kwargs)
		return args, kwargs

	def pre_consume_hooks(self, *args, **kwargs):
		return self.__process_hooks(hooks=self._pre_consume_hooks, cascade=False, *args, **kwargs)

	def post_consume_hooks(self, *args, **kwargs):
		return self.__process_hooks(hooks=self._post_consume_hooks, cascade=False, *args, **kwargs)

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
        try:
            self._data = self.conversion_methods[data.__class__](data)
        except KeyError:
            raise InvalidEventDataModification("Data of type '{_type}' was not valid for event type {cls}: {err}".format(_type=type(data), cls=self.__class__, err=traceback.format_exc()))
        except ValueError as err:
            raise InvalidEventDataModification("Malformed data: {err}".format(err=err))
        except Exception as err:
            raise InvalidEventDataModification("Unknown error occurred on modification: {err}".format(err=err))

	@property
    def created(self):
        return self._created

    @created.setter
    def created(self, timestamp):
        if not self._created is None:
            raise InvalidEventModification("Cannot alter created timestamp once it has been set.")
        else:
            self._created = timestamp

    @property
    def event_id(self):
        return self._event_id

    @event_id.setter
    def event_id(self, id):
        if not self._event_id is None:
            raise InvalidEventModification("Cannot alter event_id once it has been set.")
        else:
            self._event_id = id

	@property
    def error(self):
        return self._error

    @error.setter
    def error(self, exception):
        self._error = exception

    @property
    def formated_error(self):
    	
	def _get_timestamp(self,):
        return time.time()


def EventTimingMixin:

	_init_hooks = ["timing_init"]
	_pre_consume_hooks = ["set_started", "timeout_check"]
	_post_consume_hooks = ["set_ended", "timeout_check"]

	def timing_init(self, timing=None, timeout=None, *args, **kwargs):
		self._timing = dict() if timing is None else timing
		if not timeout is None: self.timeout = timeout
		return args, kwargs

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
        timestamp = self._get_timestamp()
        self._timing["actors"] = self._timing.get("actors", {})
        actor_obj = self._timing["actors"].get(actor_name, {})
        actor_obj["ended"] = timestamp
        self._timing["actors"][actor_name] = actor_obj
        self.__set_elapsed(timestamp=timestamp)
        return args, kwargs

    def set_started(self, actor_name, *args, **kwargs):
        timestamp = self._get_timestamp()
        self._timing["actors"] = self._timing.get("actors", {})
        actor_obj = self._timing["actors"].get(actor_name, {})
        actor_obj["started"] = timestamp
        self._timing["actors"][actor_name] = actor_obj
        self.__set_elapsed(timestamp=timestamp)
        return args, kwargs

    #misc funcs
    def timeout_check(self, *args, **kwargs):
        timeout, elapsed = self.timeout, self.elapsed
        if not timeout is None and timeout <= elapsed and timeout > 0:
            raise ActorTimeout("Timeout exceeded: Processing took longer than expected")
        return args, kwargs



class BaseEvent(object):
    _builders
    _pre_consume_hooks
    _pos_consume_hooks

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

class BaseDict(dict):
    _keys = []

    def __init__(self, *args, **kwargs):
        for key in BaseDict._keys:
            setattr(self, key, getattr(kwargs, key, None))

class HttpRequest(BaseDict):
    _keys = ["headers", "method"]


class HttpEnvironment(BaseDict):


class HttpEnvironment(dict):
    def __init__(self, *args, **kwargs):

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