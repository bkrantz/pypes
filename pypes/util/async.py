#!/usr/bin/env python
from uuid import uuid4 as uuid

import gevent
from pypes import import_restriction
from pypes.util import ignored
import signal

from gevent.pool import Pool
from gevent.greenlet import Greenlet
from greenlet import GreenletExit
from pypes.globals.async import get_async_manager, get_restart_pool, DEFAULT_SLEEP_INTERVAL
from pypes.util.errors import PypesException
from pypes.util import exception_override, ignored, RedirectStdStreams

__all__ = []

if __name__.startswith(import_restriction):
    __all__ += [
        "AsyncContextManager",
        "AsyncManager",
        "RestartPool"
    ]

def sleep(duration=DEFAULT_SLEEP_INTERVAL, *args, **kwargs):
    gevent.sleep(duration, *args, **kwargs)

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

    def __del__(self, *args, **kwargs):
        for key in self.__manager.iterkeys():
            self.remove_context_manager(key=key)
            
    @property
    def is_stopped(self):
        return self.__stopped.is_set()
    
    def __pop_stopping_threads(self): #allows start context thread to close
        is_stopped = self.is_stopped
        self.__stopped.set()
        sleep(); sleep() # bipass local and global blocks
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

    def __init__(self, sleep_interval=DEFAULT_SLEEP_INTERVAL, graceful_restart=True, irregular_restart=True, logger=None, greenlet_class=None, *args, **kwargs):
        self.sleep_interval = sleep_interval
        self.graceful_restart = graceful_restart
        self.irregular_restart = irregular_restart
        self.logger = logger
        super(RestartPool, self).__init__(greenlet_class=RestartableGreenlet, *args, **kwargs)

    def spawn(self, run, graceful_restart=None, irregular_restart=None, logger=None, parent=None, *args, **kwargs):
        """
        An override of the gevent.pool.Pool.spawn(). Exactly the same but uses the kwarg 'restart' to determine if this greenlet restarts.
        If not provided, it defaults to the pool default value
        """
        graceful_restart = self.graceful_restart if graceful_restart is None else graceful_restart
        irregular_restart = self.irregular_restart if irregular_restart is None else irregular_restart
        logger = self.logger if logger is None else logger
        new_greenlet = super(RestartPool, self).spawn(run=run, graceful_restart=graceful_restart, irregular_restart=irregular_restart, logger=logger, parent=parent, *args, **kwargs)
        new_greenlet.link_value(callback=self.__graceful_termination)
        new_greenlet.link_exception(callback=self.__irregular_termination)
        return new_greenlet

    def respawn_greenlet(self, greenlet):
        new_greenlet = self.spawn(run=greenlet.rg_run,
            graceful_restart=greenlet.rg_graceful_restart,
            irregular_restart=greenlet.rg_irregular_restart,
            logger=greenlet.rg_logger,
            suppress_std=greenlet.rg_suppress_std,
            parent=greenlet.rg_parent,
            *greenlet.rg_args,
            **greenlet.rg_kwargs)
        if not greenlet.rg_parent is None: greenlet.rg_parent.swap_thread(old_thread=greenlet, new_thread=new_greenlet)
        return new_greenlet

    def __graceful_termination(self, greenlet):
        if greenlet.graceful_restartable and (greenlet.rg_parent is None or greenlet.rg_parent.is_running()):
            self.respawn_greenlet(greenlet=greenlet)
        elif not greenlet.rg_parent is None: greenlet.rg_parent.pop_thread(old_thread=greenlet)

    def __irregular_termination(self, greenlet):
        if not isinstance(greenlet.exception, BreakoutException): # catches the breakoutexception exiting potential infinite restarts
            logger = greenlet.rg_logger
            function_name = greenlet.rg_run.__name__
            error_message = greenlet.exception

            if not logger is None: logger.error("Greenlet '{function_name}' has encountered an uncaught error: {err}".format(function_name=function_name, err=error_message))
            
            if greenlet.rg_irregular_restart:
                sleep(self.sleep_interval)
                if not logger is None: logger.info("Restarting greenlet '{function_name}'...".format(function_name=function_name))
                self.respawn_greenlet(greenlet=greenlet)
            else:
                if not greenlet.rg_parent is None: greenlet.rg_parent.pop_thread(old_thread=greenlet)
                if not greenlet.rg_suppress_std: raise greenlet.exception

    def killone(self, greenlet, exception=None, block=None, *args, **kwargs):
        return super(RestartPool, self).killone(greenlet=greenlet, exception=BreakoutException, block=False, *args, **kwargs)

    def kill(self, exception=None, block=None, *args, **kwargs):
        return super(RestartPool, self).kill(exception=BreakoutException, block=False, *args, **kwargs)

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
            suppress_std=False,
            parent=None,
            *args,
            **kwargs):
        self.rg_run = run
        self.rg_graceful_restart = graceful_restart
        self.rg_irregular_restart = irregular_restart
        self.rg_logger = logger
        self.rg_args = args
        self.rg_kwargs = kwargs
        self.rg_suppress_std = suppress_std
        assert parent is None or isinstance(parent, AsyncContextManager)
        self.rg_parent = parent
        super(RestartableGreenlet, self).__init__(run=run, *args, **kwargs)

    @property
    def running(self):
        return self.started and not self.dead

    @property
    def restartable(self):
        return self.irregular_restartable or self.graceful_restartable

    @property
    def irregular_restartable(self):
        return self.dead and isinstance(self.exception, Exception) and not isinstance(self.exception, BreakoutException) and self.rg_irregular_restart
    
    @property
    def graceful_restartable(self):
        return self.exception is None and self.dead and self.rg_graceful_restart
    
    def _report_error(self, exc_info, *args, **kwargs):
        #suppress stdout/stderr for BreakoutExceptions
        if isinstance(exc_info[1], BreakoutException) or self.rg_suppress_std:
            with RedirectStdStreams():
                value = super(RestartableGreenlet, self)._report_error(exc_info=exc_info, *args, **kwargs)
            return value
        return super(RestartableGreenlet, self)._report_error(exc_info=exc_info, *args, **kwargs)

    def kill(self, exception=None, block=None, *args, **kwargs):
        return super(RestartableGreenlet, self).kill(exception=BreakoutException, block=False, *args, **kwargs)

class AsyncContextManager(object):
    __async_class = gevent.event.Event

    def __init__(self, *args, **kwargs):
        self.__async_hidden_key = uuid().get_hex()
        self.__running = AsyncContextManager.__async_class()
        self.__running.clear()
        self.__stop = AsyncContextManager.__async_class()
        self.__stop.set()
        self.__sub_threads = []
        get_async_manager().add_context_manager(key=self.__async_hidden_key, manager=self)

    def __del__(self, *args, **kwargs):
        get_async_manager().remove_context_manager(key=self.__async_hidden_key)
        self.__kill_running_greenlets()

    def swap_thread(self, old_thread, new_thread):
        self.pop_thread(old_thread=old_thread)
        if not new_thread in self.__sub_threads: self.__sub_threads.append(new_thread)

    def pop_thread(self, old_thread):
        with ignored(ValueError):
            self.__sub_threads.remove(old_thread)

    def start(self, *args, **kwargs):
        self.__running.set()
        self.__stop.clear()
        self.__respawn_stopped_greenlets()

    def __respawn_stopped_greenlets(self):
        for greenlet in self.__sub_threads[:]: #needs to be copy as list is being edited
            if greenlet.restartable:
                get_restart_pool().respawn_greenlet(greenlet=greenlet) # already readded to sub_threads through pool

    def __kill_running_greenlets(self):
        for greenlet in self.__sub_threads: #force kills all related running threads
            if greenlet.running: get_restart_pool().killone(greenlet=greenlet)

    def stop(self, *args, **kwargs):
        self.__kill_running_greenlets()
        self.__running.clear()
        sleep() #attempt trigger exceptions

    def __enter__(self, *args, **kwargs):
        self.start(*args, **kwargs)

    def __exit__(self, *args, **kwargs):
        self.stop(*args, **kwargs)

    def spawn_thread(self, run, *args, **kwargs):
        thread = get_restart_pool().spawn(run=self.__force_running, forced_func=run, parent=self, *args, **kwargs)
        self.__sub_threads.append(thread)
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