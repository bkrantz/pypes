#!/usr/bin/env python

import gevent

from apscheduler.schedulers.gevent import GeventScheduler

from compy.actor import Actor
from compy.event import Event
from compy.actors.util.udplib import UDPInterface
from compy.actors.metas.eventgenerator import ScheduledEventProducerMeta
__all__ = [
    "EventProducer",
    "CallbackEventProducer",
    "EventGenerator",
    "CallbackEventGenerator",
    "UDPEventGenerator",
    "CallbackUDPEventGenerator",
    "CronEventGenerator",
    "CallbackCronEventGenerator",
    "UDPCronEventGenerator",
    "CallbackUDPCronEventGenerator",
]

########################
# Base Producer Actors #
########################

class EventProducer(Actor):
    '''
    Description:
        Generates a new event upon consuming an event

    Parameters:
        event_class (Optional[compysition.event.Event]):
            | The class that the generated event should be created as
            | Default: Event
        event_kwargs (Optional[int]):
            | Any additional kwargs to add to the event, including data
        generate_error (Optional[bool]):
            | Whether or not to also send the event via Actor.send_error
            | Default: False
    '''
    def __init__(self, name, event_class=Event, event_kwargs=None, *args, **kwargs):
        super(EventProducer, self).__init__(name, *args, **kwargs)
        self.event_kwargs = event_kwargs or {}
        self.output = event_class

    def _do_produce(self):
        event = self._create_event(**self.event_kwargs)
        self.logger.debug("Generated new event {event_id}".format(event_id=event.event_id))
        self.send_event(event)

    def consume(self, event, *args, **kwargs):
        self._do_produce()

class ScheduledEventProducer(EventProducer):
    '''
    Desciption:
        Continuously generates an event based on a defined interval, or if an event is consumed

    Parameters:
        producers (Optional[int]):
            | The number of greenthreads to spawn that each spawn events at the provided interval
            | Default: 1
        interval (Optional[float] OR dict):
            | The interval (in seconds) between each generated event.
            | Should have a value > 0.
            | Can also be a dict, supporting values of weeks, days, hours, minutes, and seconds
            | default: 5
        delay (Optional[float]):
            | The time (in seconds) to wait before initial event generation.
            | Default: 0
    '''

    __metaclass__ = ScheduledEventProducerMeta

    def __init__(self, name, producers=1, interval=5, delay=0, scheduler=None, *args, **kwargs):
        super(ScheduledEventProducer, self).__init__(name, *args, **kwargs)
        self.interval = self._parse_interval(interval)
        self.delay = delay
        self.producers = producers
        self.scheduler = scheduler
        if not self.scheduler:
            self.scheduler = GeventScheduler()

    def pre_hook(self):
        self._initialize_jobs()
        gevent.sleep(self.delay)
        self.scheduler.start()

    def post_hook(self):
        self.scheduler.shutdown()

    def _initialize_jobs(self):
        for producer in xrange(self.producers):
            self.scheduler.add_job(self._do_produce, self._scheduler_type, **self.interval)

##############
# Decorators #
##############

def UDP(actor_clazz):
    old_init = getattr(actor_clazz, "__init__", None)
    old_pre_hook = getattr(actor_clazz, "pre_hook", None)
    old_do_produce = getattr(actor_clazz, "_do_produce", None)

    def new_init(self, name, service="default", environment_scope='default', peers_interface=None, *args, **kwargs):
        old_init(self, name, *args, **kwargs)
        self.peers_interface = peers_interface
        if not self.peers_interface:
            self.peers_interface = UDPInterface("{0}-{1}".format(service, environment_scope), logger=self.logger)

    def new_pre_hook(self, *args, **kwargs):
        self.peers_interface.start()
        if not old_pre_hook is None:
            return old_pre_hook(self, *args, **kwargs)
            
    def new_do_produce(self):
        if not old_do_produce is None and self.peers_interface.is_master():
            return old_do_produce(self, *args, **kwargs)

    actor_clazz.__init__ = new_init
    actor_clazz.pre_hook = new_pre_hook
    actor_clazz._do_produce = new_do_produce

    return actor_clazz

def Callback(actor_clazz):
    old_init = getattr(actor_clazz, "__init__", None)
    old_do_produce = getattr(actor_clazz, "_do_produce", None)
    old_consume = getattr(actor_clazz, "consume", None)

    def new_init(self, name, is_running=False, *args, **kwargs):
        old_init(self, name, *args, **kwargs)
        self._is_running = is_running

    def new_do_produce(self):
        if not self.__is_running and not old_do_produce is None:
            self.__is_running = True
            return old_do_produce(self, *args, **kwargs)

    def new_consume(self, *args, **kwargs):
        self._is_running = False

    actor_clazz.__init__ = new_init
    actor_clazz._do_produce = new_do_produce
    actor_clazz.consume = new_consume

    return actor_clazz

#####################
# Scheduling Mixins #
#####################

class IntervalSchedulingMixin:
    '''
    Description:
        Template for defining and processing interval schedules
    '''
    DEFAULT_INTERVAL = {'weeks': 0,
                         'days': 0,
                         'hours': 0,
                         'minutes': 0,
                         'seconds': 5}

    _scheduler_type = 'interval'

    def _parse_interval(self, interval):
        _interval = {}
        _interval.update(self.DEFAULT_INTERVAL)

        if isinstance(interval, int):
            _interval['seconds'] = interval
        elif isinstance(interval, dict):
            _interval = {key:interval.get(key, value) for key, value in self.DEFAULT_INTERVAL.items()}

        return _interval

class CronSchedulingMixin:
    '''
    Description:
        Template for defining and processing cron schedules
        An EventGenerator that supports cron-style scheduling, using the following keywords: year, month, day, week, day_of_week, hour, minute, second. See 'apscheduler' documentation for specifics of configuring those keywords
    '''

    DEFAULT_INTERVAL = {'year': '*',
                        'month': '*',
                        'day': '*',
                        'week': '*',
                        'day_of_week': '*',
                        'hour': '*',
                        'minute': '*',
                        'second': '*/12'}

    _scheduler_type = 'interval'

    def _parse_interval(self, interval):
        _interval = self.DEFAULT_INTERVAL
        if isinstance(interval, dict):
            _interval = {key:str(interval.get(key, value)) for key, value in self.DEFAULT_INTERVAL.items()}
        return _interval

###############
# User Actors #
###############

EventProducer = EventProducer

@UDP
class UDPEventProducer(EventProducer):
    pass

@Callback
class CallbackEventProducer(EventProducer):
    pass

class EventGenerator(IntervalSchedulingMixin, ScheduledEventProducer):
    pass

@Callback
class CallbackEventGenerator(IntervalSchedulingMixin, ScheduledEventProducer):
    pass

@UDP
class UDPEventGenerator(IntervalSchedulingMixin, ScheduledEventProducer):
    pass

@UDP
@Callback
class CallbackUDPEventGenerator(IntervalSchedulingMixin, ScheduledEventProducer):
    pass

class CronEventGenerator(CronSchedulingMixin, ScheduledEventProducer):
    pass

@Callback
class CallbackCronEventGenerator(CronSchedulingMixin, ScheduledEventProducer):
    pass

@UDP
class UDPCronEventGenerator(CronSchedulingMixin, ScheduledEventProducer):
    pass

@UDP
@Callback
class CallbackUDPCronEventGenerator(CronSchedulingMixin, ScheduledEventProducer):
    pass