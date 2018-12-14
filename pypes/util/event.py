#!/usr/bin/env python
import collections

from lxml import etree

from pypes import import_restriction

__all__ = []

if __name__.startswith(import_restriction):
    __all__ += [
        "ConversionMethods",
        "get_conversion_methods"
    ]

class ConversionMethods:
    _XML_TYPES = [etree._Element, etree._ElementTree, etree._XSLTResultTree]
    _JSON_TYPES = [dict, list, collections.OrderedDict]

    __compy_wrapper_key = "compy_conversion_wrapper"
    __compy_json_type_key = "@compy_json_type"

    def get_conversion_methods(self, conv_type=None):
        if conv_type == "XML":
            conversion_methods = {str: lambda data: etree.fromstring(data)}
            conversion_methods.update(dict.fromkeys(self._XML_TYPES, lambda data: data))
            conversion_methods.update(dict.fromkeys(self._JSON_TYPES, lambda data: etree.fromstring(xmltodict.unparse(self.__internal_xmlify(data)).encode('utf-8'))))
            conversion_methods.update({None.__class__: lambda data: etree.fromstring("<root/>")})
            return conversion_methods
        elif conv_type == "JSON":
            conversion_methods = {str: lambda data: json.loads(data)}
            conversion_methods.update(dict.fromkeys(self._JSON_TYPES, lambda data: json.loads(json.dumps(data, default=self.decimal_default))))
            conversion_methods.update(dict.fromkeys(self._XML_TYPES, lambda data: self.__remove_internal_xmlify(xmltodict.parse(etree.tostring(data), expat=expat))))
            conversion_methods.update({None.__class__: lambda data: {}})
            return conversion_methods
        else:
            return collections.defaultdict(lambda: lambda data: data)

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
        text = dict_obj.get("#text", None)
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

    def decimal_default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError