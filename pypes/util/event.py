#!/usr/bin/env python
import collections
import json
from lxml import etree

from pypes import import_restriction
from pypes.util.errors import InvalidEventDataModification, InvalidEventConversion
'''
__all__ = []

if __name__.startswith(import_restriction):
    __all__ += [
        "ConversionMethods",
        "get_conversion_methods"
    ]
'''
#event data type definitions
class JSONType: pass
class XMLType: pass
class StringType: pass
class DefaultType: pass

class EventManager:
    __XML_TYPES = [etree._Element, etree._ElementTree, etree._XSLTResultTree]
    __JSON_TYPES = [dict, list, collections.OrderedDict]

    __pypes_xml_wrapper_key = "pypes_conversion_wrapper"
    __pypes_json_type_key = "@pypes_json_type"

    __xml_conversion_methods = {str: lambda data: etree.fromstring(data)}
    __xml_conversion_methods.update(dict.fromkeys(__XML_TYPES, lambda data: data))
    __xml_conversion_methods.update(dict.fromkeys(__JSON_TYPES, lambda data: etree.fromstring(xmltodict.unparse(self.__internal_xmlify(data)).encode('utf-8'))))
    __xml_conversion_methods.update({None.__class__: lambda data: etree.fromstring("<%s/>" % __pypes_xml_wrapper_key)})
    __json_conversion_methods = {str: lambda data: json.loads(data)}
    __json_conversion_methods.update(dict.fromkeys(__JSON_TYPES, lambda data: json.loads(json.dumps(data, default=self.__decimal_default))))
    __json_conversion_methods.update(dict.fromkeys(__XML_TYPES, lambda data: self.__remove_internal_xmlify(xmltodict.parse(etree.tostring(data), expat=expat))))
    __json_conversion_methods.update({None.__class__: lambda data: {}})
    __string_conversion_methods = {str: lambda data: data}
    __string_conversion_methods.update(dict.fromkeys(__JSON_TYPES, lambda data: json.dumps(data, default=self.__decimal_default)))
    __string_conversion_methods.update(dict.fromkeys(__XML_TYPES, lambda data: etree.tostring(data)))
    __string_conversion_methods.update({None.__class__: lambda data: ""})
    __default_conversion_methods = collections.defaultdict(lambda: lambda data: data)

    convert_to_xml = lambda self, value: self.__xml_conversion_methods[value.__class__](data=value)
    convert_to_json = lambda self, value: self.__json_conversion_methods[value.__class__](data=value)
    convert_to_string = lambda self, value: self.__string_conversion_methods[value.__class__](data=value)
    convert_to_default = lambda self, value: self.__default_conversion_methods[value.__class__](data=value)

    __conversion_types = {
        JSONType: convert_to_json,
        XMLType: convert_to_xml,
        StringType: convert_to_string,
        DefaultType: convert_to_default
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
            return self.__conversion_types[event._format_type](self=self, value=new_value)
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
            except Exception as err:
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
