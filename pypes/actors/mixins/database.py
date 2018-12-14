import json

from lxml import etree

from compy.mixins.actor import JSONEventModifyMixin, XMLEventModifyMixin, LookupMixin, XPathLookupMixin

__all__ = []

if __name__.startswith('compy.'):
    __all__ += [
        "_DatabaseMixin",
		"_XMLDatabaseMixin",
		"_JSONDatabaseMixin"
    ]

class _DatabaseMixin:
	_output_funcs = {
		"ignore": "ignore_results",
		"join": "join_results",
		"update": "update_results",
		"replace": "replace_results",
		"delete": "delete_results",
		"attach": "attach_results"
	}

	def ignore_results(self, event, results):
		return event

	def attach_results(self, event, results):
		for result in results:
			for attr, value in result.iteritems():
				event.set(attr, value)
			break
		return event

	def join_results(self, event, results):
		formatted_results = self._format_results(event=event, results=results)
		return self.event_join(event=event, content=formatted_results, key_chain=self.response_scope[:], join_key=self.join_key)

	def update_results(self, event, results):
		formatted_results = self._format_results(event=event, results=results)
		return self.event_update(event=event, content=formatted_results, key_chain=self.response_scope[:])

	def delete_results(self, event, results):
		return self.event_delete(event=event, content=None, key_chain=self.response_scope[:])

	def replace_results(self, event, results):
		formatted_results = self._format_results(event=event, results=results)
		return self.event_replace(event=event, content=formatted_results, key_chain=self.response_scope[:])

	def format_output(self, event, results):
		return getattr(self, self._output_funcs[self.output_mode])(event=event, results=results)


class _XMLDatabaseMixin(XMLEventModifyMixin, _DatabaseMixin, XPathLookupMixin):
	def _get_dynamic_params(self, event):
		param_groups = []
		dynamic_scopes = self.lookup(obj=event, key_chain=self.param_scope)
		for dynamic_scope in dynamic_scopes:
			params = {}
			try:
				children = list(dynamic_scope)
			except TypeError:
				pass #ignores None scopes
			else:
				for child in children:
					try:
						if params.get(child.tag, None) is None:
							params[child.tag] = child.text
					except AttributeError:
						pass
				param_groups.append(params)

		return param_groups

	def _format_results(self, event, results):
		root = etree.Element(self.records_key)
		for result in results:
			result_child = etree.SubElement(root, self.record_key)
			for key, value in result.iteritems():
				current_field = etree.SubElement(result_child, key)
				current_field.text = str(value)
		return root

class _JSONDatabaseMixin(JSONEventModifyMixin, _DatabaseMixin, LookupMixin):

	def __interpret_single(self, dict):
		params = {}
		for key, value in dict.iteritems():
			params[key] = str(value)
			'''
			try:
				params[key] = json.dumps(value)
			except AttributeError, ValueError:
				params[key] = str(value)
			'''
		return params

	def _get_dynamic_params(self, event):
		param_groups = []
		dynamic_scope = self.lookup(obj=event, key_chain=self.param_scope)
		try:
			param_groups.append(self.__interpret_single(dynamic_scope))
		except AttributeError:
			try:
				for child in dynamic_scope:
					param_groups.append(self.__interpret_single(child))
			except TypeError:
				pass
		return param_groups

	def _format_results(self, event, results):
		return {self.records_key:[result for result in results if result]}