import time
from compy.actors.mixins.eventjoin import DefaultJoinMixin, XMLJoinMixin, JSONJoinMixin
from compy.actors.metas.eventjoin import BaseMatchedEventBoxMeta
__all__ = [
    "MatchedEventBox",
    "MatchedXMLEventBox",
    "MatchedJSONEventBox"
]

class BaseMatchedEventBox(object):

    __metaclass__ = BaseMatchedEventBoxMeta

    def __init__(self, inboxes, key="joined_root"):
        self.inboxes_reported = {}
        self.key = key
        self.created = time.time()
        if not isinstance(inboxes, list):
            inboxes = [inboxes]
        self.inboxes_reported = {inbox: False for inbox in inboxes}

    def report_inbox(self, inbox_name, data):
        if self.inboxes_reported[inbox_name] == False:
            self.inboxes_reported[inbox_name] = data
        else:
            raise Exception("Inbox {0} already reported for event. Ignoring".format(inbox_name))

    def all_inboxes_reported(self):
        for key, value in self.inboxes_reported.iteritems():
            if value == False:
                return False
        return True

class MatchedEventBox(DefaultJoinMixin, BaseMatchedEventBox):
    pass

class MatchedXMLEventBox(XMLJoinMixin, BaseMatchedEventBox):
    pass

class MatchedJSONEventBox(JSONJoinMixin, BaseMatchedEventBox):
    pass