#!/usr/bin/env python

from pypes.util.async import AsyncContextManager, sleep
from pypes.globals.async import get_async_manager
from pypes.event import Event, BaseEvent
from pypes.metas.actor import ActorMeta
from pypes.util import ignored, fixed_returns
from pypes.util.queue import QueuePool, Queue
from pypes.util.logger import Logger
from pypes.util.errors import (QueueConnected, InvalidActorOutput, QueueEmpty, InvalidEventConversion, InvalidActorInput, QueueFull, PypesException)
import time
from pypes.globals.event import get_event_manager

__all__ = [
    "Actor"
]

class Actor(AsyncContextManager):

    __metaclass__ = ActorMeta

    input = Event
    output = Event

    REQUIRED_EVENT_ATTRIBUTES = None

    def __init__(self,
            name,
            size=0,
            convert_output=False,
            *args,
            **kwargs):
        self.name = name
        self.__pool = QueuePool(size)
        self.__logger = Logger(name, self.pool.logs)
        self.convert_output = convert_output
        super(Actor, self).__init__(self, *args, **kwargs)

    @property
    def pool(self):
        return self.__pool

    @property
    def logger(self):
        return self.__logger

    @property
    def size(self):
        return self.__pool.size

    def __connect_queue(self, source_queue_name="outbox", destination=None, destination_queue_name="inbox", pool_scope=None, check_existing=True):
        """Connects the <source_queue_name> queue to the <destination> queue.
        If the destination queue already exists, the source queue is changed to be a reference to that queue, as Many to One connections
        are supported, but One to Many is not"""

        source_queue = pool_scope.get(source_queue_name, None)
        destination_queue = destination.pool.inbound.get(destination_queue_name, None)

        if check_existing:
            if not source_queue is None:
                raise QueueConnected("Outbound queue {queue_name} on {source_name} is already connected".format(queue_name=source_queue_name, source_name=self.name))
            if not destination_queue is None:
                raise QueueConnected("Inbound queue {queue_name} on {destination_name} is already connected".format(queue_name=destination_queue_name, destination_name=destination.name))

        if source_queue is None:
            if destination_queue is None:
                source_queue = pool_scope.add(name=source_queue_name)
                destination.__register_consumer(queue_name=destination_queue_name, queue=source_queue)
            elif destination_queue:
                pool_scope.add(name=source_queue_name, queue=destination_queue)

        else:
            if destination_queue is None:
                destination.__register_consumer(queue_name=destination_queue_name, queue=source_queue)
            else:
                source_queue.dump(other_queue=destination_queue)
                pool_scope.add(name=destination_queue.name, queue=destination_queue)

        self.logger.info("Connected queue '{origin_queue_name}' to '{destination_actor_name}.{destination_queue_name}'".format(origin_queue_name=source_queue_name, destination_actor_name=destination.name, destination_queue_name=destination_queue_name))

    def __register_consumer(self, queue_name, queue):
        self.pool.inbound.add(name=queue_name, queue=queue)
        self.spawn_thread(run=self.__consumer, origin_queue=queue)

    def __loop_send(self, event, destination_queues):
        event_func = lambda event: event
        if len(destination_queues) > 1:
            event.splits.append(self.__generate_split_id(event=event))
            event_func = lambda event: event.clone()
        
        with ignored(AttributeError):
            destination_queues = destination_queues.itervalues()
        for queue in destination_queues:
            queue.put(element=event_func(event))

    def __generate_split_id(self, event):
        raw = hash("%s%s%s" % (event.event_id, self.name, str(time.time())))
        return hash(raw)

    def __consumer(self, origin_queue, timeout=10, *args, **kwargs):
        #run loop
        while self.is_running():
            origin_queue.wait_until_content()
            self.__try_spawn_consume(origin_queue=origin_queue, timeout=timeout)
            sleep()
        sleep()

    def __try_spawn_consume(self, origin_queue, timeout=None):
        try:
            event = origin_queue.get(block=True, timeout=timeout) if not timeout is None else origin_queue.get()
        except QueueEmpty:
            pass
        else:
            self.spawn_thread(run=self.__do_consume, event=event, origin_queue=origin_queue, graceful_restart=False, irregular_restart=False)

    def __consume_pre_processing(self, event, origin_queue):
        try:

            if not get_event_manager().is_instance(event=event, convert_to=self.input):
                new_event = get_event_manager().convert(event=event, convert_to=self.input)
                self.logger.warning("Incoming event was of type '{_type}' when type {input} was expected. Converted to {converted}".format(
                    _type=type(event), input=self.input, converted=type(new_event)), event=event)
                event = new_event
        except InvalidEventConversion as err:
            self.logger.error("Event was of type '{_type}', expected '{input}'".format(_type=type(event), input=self.input))
            raise err
        try:
            if not self.REQUIRED_EVENT_ATTRIBUTES is None:
                missing = [attribute for attribute in self.REQUIRED_EVENT_ATTRIBUTES if not event.get(attribute, None)]
                if len(missing) > 0:
                    raise InvalidActorInput("Required incoming event attributes were missing: {missing}".format(missing=missing))
        except InvalidActorInput as err:
            self.logger.error("Invalid input detected: {0}".format(err))
            raise err
        event.pre_consume_hooks(actor_name=self.name)
        return event

    def __consume_post_processing(self, event, destination_queues):
        event.post_consume_hooks(actor_name=self.name)
        if not get_event_manager().is_instance(event=event, convert_to=self.output):
            raise_error = True
            if self.convert_output:
                raise_error = False
                try:
                    new_event = get_event_manager().convert(event=event, convert_to=self.output)
                    self.logger.warning("Outgoing event was of type '{_type}' when type {output} was expected. Converted to {converted}".format(
                        _type=type(event), output=self.output, converted=type(new_event)), event=event)
                    event = new_event
                except InvalidEventConversion:
                    raise_error = True
            if raise_error:
                raise InvalidActorOutput("Event was of type '{_type}', expected '{output}'".format(_type=type(event), output=self.output))
        return event

    def __consume_wrapper(self, event, origin_queue):
        value = self.consume(event=event, origin_queue=origin_queue)
        event, queues = fixed_returns(actual_return=value, num_returns=2)
        return self.__format_event(event=event), self.__format_queues(queues=queues)

    def __format_event(self, event):
        if not event is None and not isinstance(event, BaseEvent):
            self.logger.error("Actor '%s' produced an invalid event" % self.name)
            raise PypesException()
        return event

    def __format_queues(self, queues):
        queues = queues.values() if isinstance(queues, dict) else queues
        queues = list(queues) if isinstance(queues, tuple) else queues
        queues = [queues] if isinstance(queues, Queue) else queues
        try:
            if isinstance(queues, list):
                for queue in queues:
                    if not isinstance(queue, Queue):
                        raise TypeError()
            elif not queues is None:
                raise TypeError()
        except TypeError:
            self.logger.error("Actor '%s' produced invalid destination queues '%s'" % (self.name, queues))
            raise PypesException()
        return queues

    def __do_consume(self, event, origin_queue):
        try:
            event = self.__consume_pre_processing(event=event, origin_queue=origin_queue)
            event, destination_queues = self.__consume_wrapper(event=event, origin_queue=origin_queue)
            event = self.__consume_post_processing(event=event, destination_queues=destination_queues)
            if not event is None:
                self.__send_event(event=event, destination_queues=destination_queues)
        except QueueFull as err:
            origin_queue.wait_until_free()
            origin_queue.put(element=event)
        except Exception as err:
            event.error = err
            self.__send_error(event=event)

    def __send_event(self, event, destination_queues=None):
        destination_queues = self.pool.outbound if destination_queues is None else destination_queues
        self.__loop_send(event=event, destination_queues=destination_queues)

    def __send_error(self, event):
        self.__loop_send(event=event, destination_queues=self.pool.error)

    def create_event(self, *args, **kwargs):
        try:
            return self.output(**kwargs)
        except TypeError:
            raise ValueError("Unable to create event: Invalid type definition")

    def connect_error_queue(self, destination_queue_name="inbox", *args, **kwargs):
        self.__connect_queue(pool_scope=self.pool.error, destination_queue_name="error_{0}".format(destination_queue_name), *args, **kwargs)

    def connect_log_queue(self, destination_queue_name="inbox", *args, **kwargs):
        self.__connect_queue(pool_scope=self.pool.logs, destination_queue_name="log_{0}".format(destination_queue_name), *args, **kwargs)

    def connect_queue(self, *args, **kwargs):
        self.__connect_queue(pool_scope=self.pool.outbound, *args, **kwargs)

    def start(self):
        super(Actor, self).start()
        if hasattr(self, "pre_hook"):
            self.logger.debug("Executing pre_hook()")
            self.pre_hook()
        self.logger.debug("Started with max queue size of {size} events".format(size=self.size))

    def stop(self):
        if hasattr(self, "post_hook"):
            self.logger.debug("Executing post_hook()")
            self.post_hook()
        super(Actor, self).stop()