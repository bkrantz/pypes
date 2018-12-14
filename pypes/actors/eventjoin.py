#!/usr/bin/env python

import traceback
import gevent
import time

from compy.actor import Actor
from compy.event import XMLEvent, JSONEvent
from compy.actors.util.eventjoin import MatchedEventBox, MatchedXMLEventBox, MatchedJSONEventBox

class EventJoin(Actor):
    '''**Holds event data until all inbound queues have reported in with events with a matching event_id, then aggregates the data
    and sends it on**

    Parameters:

        name (str):
            | The instance name.
        purge_delay (Optional[int]):
            | If set, determines the interval that events are purged, rather than staying in memory
            | waiting for the other messages. Useful in the event that a certain split event has errored out on
            | one of it's paths to rejoin the main flow. A value of 0 indicates that no purges occur
            | Default: 0

    '''

    matched_event_class = MatchedEventBox

    def __init__(self, name, purge_delay=None, key=None, *args, **kwargs):
        super(EventJoin, self).__init__(name, *args, **kwargs)
        self.event_boxes = {}
        self.key = name if key is None else key
        self.purge_delay = purge_delay

    def pre_hook(self):
        if not self.purge_delay is None and self.purge_delay > 0:
            self.threads.spawn(self.event_purger)

    def event_purger(self):
        while self.loop():
            event_box_keys = self.event_boxes.keys()
            for key in event_box_keys:
                event_box = self.event_boxes.get(key, None)
                if not event_box is None:
                    purge_time = event_box.created + self.purge_delay
                    if purge_time <= time.time():
                        del self.event_boxes[key]
            gevent.sleep(self.purge_delay)

    def consume(self, event, origin_queue=None, *args, **kwargs):
        existing_event_box = self.event_boxes.get(event.event_id, None)
        try:
            if existing_event_box is None:
                self.event_boxes[event.event_id] = self.matched_event_class(self.pool.inbound.values(), key=self.key)
                existing_event_box = self.event_boxes.get(event.event_id, None)
            existing_event_box.report_inbox(origin_queue, event.data)
            if existing_event_box.all_inboxes_reported():
                event.data = existing_event_box.joined
                self.send_event(event)
                del self.event_boxes[event.event_id]
                return event, None
        except Exception:
            self.logger.warn("Could not process incoming event: {0}".format(traceback.format_exc()), event=event)


class XMLEventJoin(EventJoin):

    input = XMLEvent
    output = XMLEvent
    matched_event_class = MatchedXMLEventBox


class JSONEventJoin(EventJoin):

    input = JSONEvent
    output = JSONEvent
    matched_event_class = MatchedJSONEventBox
