from compy.actors.mixins.event import LookupMixin, XPathLookupMixin

__all__ = [
	"get_lookup_mixin",
	"get_xpath_lookup_mixin"
]

_lookup_mixin = None
_xpath_lookup_mixin = None

def get_lookup_mixin():
    global _lookup_mixin
    if _lookup_mixin is None:
        _lookup_mixin = LookupMixin()
    return _lookup_mixin

def get_xpath_lookup_mixin():
    global _xpath_lookup_mixin
    if _xpath_lookup_mixin is None:
        _xpath_lookup_mixin = XPathLookupMixin()
    return _xpath_lookup_mixin