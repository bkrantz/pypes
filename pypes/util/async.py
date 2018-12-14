#!/usr/bin/env python
from uuid import uuid4 as uuid

import gevent
from pypes import import_restriction
from pypes.util import ignored
import signal

from gevent.pool import Pool
from gevent.greenlet import Greenlet
from greenlet import GreenletExit
from pypes.globals.async import get_async_manager, get_restart_pool
from pypes.util.errors import PypesException
from pypes.util import exception_override, ignored
__all__ = []

if __name__.startswith(import_restriction):
    __all__ += [
        "AsyncContextManager",
        "AsyncManager",
        "RestartPool"
    ]

class BreakoutException(Exception):
    pass

class AsyncManager:
    '''
    INTENDED USAGE

    with get_async_manager() as async_manager:
        async_manager.wait_for_stop()

    #which runs until interrupt or termination signal is received
    '''

    def __init__(self, *args, **kwargs):
        self.__managers = {}
        gevent.signal(signal.SIGINT, self.trigger_stop)
        gevent.signal(signal.SIGTERM, self.trigger_stop)
        self.__stopped = gevent.event.Event()
        self.trigger_stop()

    @property
    def is_stopped(self):
        return self.__stopped.is_set()
    
    def __pop_stopping_threads(self): #allows start context thread to close
        is_stopped = self.is_stopped
        self.__stopped.set()
        self.sleep() #bipass local block
        self.sleep() #bipass global block
        if not is_stopped:
            self.__stopped.clear()

    def __try_stop_single(self, manager):
        if manager.is_running():
            manager.trigger_stop()

    def __try_start_single(self, manager):
        if not manager.is_running():
            get_restart_pool().spawn(run=self.__single_start, manager=manager, graceful_restart=False, irregular_restart=False)

    def __single_start(self, manager):
        with manager:
            manager.wait_for_stop()
            self.wait_for_stop()

    def __enter__(self, block=None, *args, **kwargs):
        self.__stopped.clear()
        for manager in self.__managers.itervalues():
            self.__try_start_single(manager=manager)

    def __exit__(self, *args, **kwargs):
        for manager in self.__managers.itervalues():
            self.__try_stop_single(manager=manager)
        self.__pop_stopping_threads() 

    def sleep(self, duration=0, *args, **kwargs):
        gevent.sleep(duration)

    def wait_for_stop(self):
        self.__stopped.wait()

    def trigger_stop(self):
        self.__stopped.set()

    def add_context_manager(self, key, manager):
        assert isinstance(manager, AsyncContextManager)
        self.__managers[key] = manager
        if not self.is_stopped:
            self.__try_start_single(manager=manager)

    def remove_context_manager(self, key):
        try:
            manager = self.__managers.pop(key)
        except KeyError:
            pass
        else:
            if not self.is_stopped:
                self.__try_stop_single(manager=manager)
                self.__pop_stopping_threads()

class RestartPool(Pool):
    """
    A simple extension of the gevent Pool class that, by default, adds a callback to all greenlet spawns that will
    restart the greenlet in the event of an exceptional exit

    Additional parameters:
        - restart       (bool):     (Default: True) This flag is designed to be used as a signifier to a linked exception callback
                                        as to whether or not the callback should spawn a new greenlet to replace the one that crashed.
                                        If true, the callback should try to spawn a new greenlet. If false, the greenlet function stays dead
        - sleep_interval (int):     (Default: 0) The amount of time to sleep between greenlet restarts. A value of 0 may not be appropriate, as it could bring
                                        an application or process to its knees
        - logger      (Logger):     (Default: None) This should be an instance of a logger that emulates the "warn, error, info" python log levels. If one is
                                        provided, the greenlet restart will be directed to that log file as well as STDOUT

    """

    def __init__(self, sleep_interval=0, graceful_restart=True, irregular_restart=True, logger=None, greenlet_class=None, *args, **kwargs):
        self.sleep_interval = sleep_interval
        self.graceful_restart = graceful_restart
        self.irregular_restart = irregular_restart
        self.logger = logger
        self.__greenlet_dict = {}
        super(RestartPool, self).__init__(greenlet_class=RestartableGreenlet, *args, **kwargs)

    def get_greenlet(self, key):
        return self.__greenlet_dict.get(key, None)

    def pop_greenlet(self, key):
        return self.__greenlet_dict.pop(key, None)

    def reset(self):
        self.kill()
        self.__greenlet_dict = {}

    def spawn(self, run, key=None, graceful_restart=None, irregular_restart=None, logger=None, *args, **kwargs):
        """
        An override of the gevent.pool.Pool.spawn(). Exactly the same but uses the kwarg 'restart' to determine if this greenlet restarts.
        If not provided, it defaults to the pool default value
        """
        graceful_restart = self.graceful_restart if graceful_restart is None else graceful_restart
        irregular_restart = self.irregular_restart if irregular_restart is None else irregular_restart
        logger = self.logger if logger is None else logger
        new_greenlet = super(RestartPool, self).spawn(run=run, graceful_restart=graceful_restart, irregular_restart=irregular_restart, logger=logger, key=key, *args, **kwargs)
        new_greenlet.link_value(callback=self.__graceful_termination)
        new_greenlet.link_exception(callback=self.__irregular_termination)
        self.__greenlet_dict[new_greenlet.rg_key] = new_greenlet
        return new_greenlet

    def respawn_greenlet(self, greenlet):
        new_greenlet = self.spawn(run=greenlet.rg_run,
            graceful_restart=greenlet.rg_graceful_restart,
            irregular_restart=greenlet.rg_irregular_restart,
            logger=greenlet.rg_logger,
            key=greenlet.rg_key,
            *greenlet.rg_args,
            **greenlet.rg_kwargs)
        self.__greenlet_dict[new_greenlet.rg_key] = new_greenlet
        return new_greenlet

    def __graceful_termination(self, greenlet):
        greenlet.running = False
        if greenlet.rg_graceful_restart:
            self.respawn_greenlet(greenlet=greenlet)
        else:
            self.pop_greenlet(key=greenlet.rg_key) #ran it's coarse and will no longer be tracked

    def __irregular_termination(self, greenlet):
        greenlet.running = False
        if not isinstance(greenlet.exception, BreakoutException):
            logger = greenlet.rg_logger
            function_name = greenlet.rg_run.__name__
            error_message = greenlet.exception

            if not logger is None:
                logger.error("Greenlet '{function_name}' has encountered an uncaught error: {err}".format(function_name=function_name, err=error_message))
            if greenlet.rg_irregular_restart:
                get_async_manager().sleep(self.sleep_interval)
                if not logger is None:
                    logger.info("Restarting greenlet '{function_name}'...".format(function_name=function_name))
                self.respawn_greenlet(greenlet=greenlet)
            else:
                self.pop_greenlet(key=greenlet.rg_key) #ran it's coarse and will no longer be tracked
                raise greenlet.exception

    def kill(self, exception=None, *args, **kwargs):
        return super(RestartPool, self).kill(exception=BreakoutException, block=False)

class RestartableGreenlet(Greenlet):
    """
    A simple extension of the greenlet class that keeps track of the the run target
    and targets args/kwargs, as the base Greenlet deletes these values at the end of 'run'
    We can then use these properties in the callback to start a new greenlet to replace the failed greenlet automatically,
    if we so desire.

    Additional parameters:
        - restart (bool):   (Default: True) This flag is designed to be used as a signifier to a linked exception callback
                                        as to whether or not the callback should spawn a new greenlet to replace the one that crashed.
                                        If true, the callback should try to spawn a new greenlet. If false, the greenlet function stays dead

    """

    def __init__(self,
            run,
            graceful_restart=True,
            irregular_restart=True,
            logger=None,
            key=None,
            *args,
            **kwargs):
        self.rg_run = run
        self.rg_graceful_restart = graceful_restart
        self.rg_irregular_restart = irregular_restart
        self.rg_logger = logger
        self.rg_key = uuid().get_hex() if key is None else key
        self.rg_args = args
        self.rg_kwargs = kwargs
        self.__running = True
        super(RestartableGreenlet, self).__init__(run=run, *args, **kwargs)

    @property
    def running(self):
        return self.__running

    @running.setter
    def running(self, running):
        self.__running = bool(running)
    
    def _report_error(self, exc_info, *args, **kwargs):
        if isinstance(exc_info[1], BreakoutException):
            return
        return super(RestartableGreenlet, self)._report_error(exc_info=exc_info, *args, **kwargs)

    def kill(self, exception=None, *args, **kwargs):
        return super(RestartableGreenlet, self).kill(exception=BreakoutException, block=False)

class AsyncContextManager(object):
    __async_class = gevent.event.Event

    def __init__(self, *args, **kwargs):
        self.__async_hidden_key = uuid().get_hex()
        self.__running = AsyncContextManager.__async_class()
        self.__running.clear()
        self.__stop = AsyncContextManager.__async_class()
        self.__stop.set()
        self.__sub_thread_keys = []
        get_async_manager().add_context_manager(key=self.__async_hidden_key, manager=self)

    def __del__(self, *args, **kwargs):
        get_async_manager().remove_context_manager(key=self.__async_hidden_key)

    def start(self, *args, **kwargs):
        self.__running.set()
        self.__stop.clear()
        for thread_key in self.__sub_thread_keys: #starts all related non running threads
            thread = get_restart_pool().get_greenlet(key=thread_key)
            if not thread.running: get_restart_pool().respawn_greenlet(greenlet=thread)

    def stop(self, *args, **kwargs):
        self.__running.clear()
        for thread_key in self.__sub_thread_keys: #force kills all related running threads
            greenlet = get_restart_pool().get_greenlet(key=thread_key)
            if greenlet.running: greenlet.kill()

    def __enter__(self, *args, **kwargs):
        self.start(*args, **kwargs)

    def __exit__(self, *args, **kwargs):
        self.stop(*args, **kwargs)

    def spawn_thread(self, run, *args, **kwargs):
        thread = get_restart_pool().spawn(run=self.__force_running, forced_func=run, *args, **kwargs)
        self.__sub_thread_keys.append(thread.rg_key)
        return thread

    def __force_running(self, forced_func, *args, **kwargs):
        self.wait_for_running()
        forced_func(*args, **kwargs)

    def is_running(self):
        return self.__running.is_set()

    def wait_for_running(self):
        self.__running.wait()

    def wait_for_stop(self):
        self.__stop.wait()

    def trigger_stop(self):
        self.__stop.set()