from lxml import etree

__all__ = []

if __name__ == "":
    __all__ += [
        "DefaultJoinMixin",
        "XMLJoinMixin",
        "JSONJoinMixin"
    ]

class DefaultJoinMixin:

    @property
    def joined(self):
        return [data for data in self.inboxes_reported.itervalues()]

class XMLJoinMixin:

    @property
    def joined(self):
        root = etree.Element(self.key)
        map(lambda xml: root.append(xml), self.inboxes_reported.itervalues())
        return root

class JSONJoinMixin:

    @property
    def joined(self):
        return {k: v for d in self.inboxes_reported.itervalues() for k, v in d.iteritems()}
