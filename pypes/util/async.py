#!/usr/bin/env python
from uuid import uuid4 as uuid

import gevent
from pypes import import_restriction
from pypes.util import ignored
import signal
import time
from gevent.pool import Pool
from gevent.greenlet import Greenlet, killall, joinall
from greenlet import GreenletExit
from pypes.globals.async import get_async_manager, get_restart_pool, DEFAULT_SLEEP_INTERVAL
from pypes.util.errors import PypesException
from pypes.util import exception_override, ignored, RedirectStdStreams
from pypes.metas.async import KilledExceptionMeta, AsyncManagerMeta, RestartPoolMeta, RestartableGreenletMeta, AsyncContextManagerMeta
__all__ = []

if __name__.startswith(import_restriction):
    __all__ += [
        "AsyncContextManager",
        "AsyncManager",
        "RestartPool",
        "KilledException"
    ]

def sleep(duration=DEFAULT_SLEEP_INTERVAL, *args, **kwargs):
    gevent.sleep(duration, *args, **kwargs)

def timestamp():
    return time.time()
    
class KilledException(Exception):
    __metaclass__ = KilledExceptionMeta

class AsyncManager:
    '''
    INTENDED USAGE

    with get_async_manager() as async_manager:
        async_manager.wait_for_stop()

    #which runs until interrupt or termination signal is received
    '''

    __metaclass__ = AsyncManagerMeta

    def __init__(self, *args, **kwargs):
        self.__managers = {}
        gevent.signal(signal.SIGINT, self.trigger_stop)
        gevent.signal(signal.SIGTERM, self.trigger_stop)
        self.__stopped = gevent.event.Event()
        self.trigger_stop()

    def __del__(self, *args, **kwargs):
        for key in self.__managers.keys():
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
        stopping_greenlets = []
        if manager.is_running():
            manager.trigger_stop()
            stopping_greenlets += manager.greenlets
        assert manager.is_stopping()
        return stopping_greenlets

    def __try_start_single(self, manager):
        if not manager.is_running():
            get_restart_pool().spawn(run=self.__single_start, greenlet_manager=manager, manager=manager, graceful_restart=False, rough_restart=False)

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
        joinall(greenlets=get_restart_pool().greenlets)

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
                stopping_greenlets = self.__try_stop_single(manager=manager)
                joinall(greenlets=stopping_greenlets)

class RestartPool(Pool):
    """
    A simple extension of the gevent Pool class that, by default, adds a callback to all greenlet spawns that will
    restart the greenlet in the event of an exceptional exit

    Additional parameters:
        - restart       (bool):     (Default: True) This flag is designed to be used as a signifier to a linked exception callback
                                        as to whether or not the callback should spawn a new greenlet to replace the one that crashed.
                                        If true, the callback should try to spawn a new greenlet. If false, the greenlet function stays dead
        - restart_sleep_interval (int):     (Default: 0) The amount of time to sleep between greenlet restarts. A value of 0 may not be appropriate, as it could bring
                                        an application or process to its knees
        - logger      (Logger):     (Default: None) This should be an instance of a logger that emulates the "warn, error, info" python log levels. If one is
                                        provided, the greenlet restart will be directed to that log file as well as STDOUT

    """

    __metaclass__ = RestartPoolMeta

    def __init__(self, restart_sleep_interval=DEFAULT_SLEEP_INTERVAL, graceful_restart=True, rough_restart=True, logger=None, greenlet_class=None, *args, **kwargs):
        self.restart_sleep_interval = restart_sleep_interval
        self.graceful_restart = graceful_restart
        self.rough_restart = rough_restart
        self.logger = logger
        super(RestartPool, self).__init__(greenlet_class=RestartableGreenlet, *args, **kwargs)

    def spawn(self, run, greenlet_manager, graceful_restart=None, rough_restart=None, logger=None, *args, **kwargs):
        """
        An override of the gevent.pool.Pool.spawn(). Exactly the same but uses the kwarg 'restart' to determine if this greenlet restarts.
        If not provided, it defaults to the pool default value
        """
        graceful_restart = self.graceful_restart if graceful_restart is None else graceful_restart
        rough_restart = self.rough_restart if rough_restart is None else rough_restart
        logger = self.logger if logger is None else logger
        new_greenlet = super(RestartPool, self).spawn(run=run, graceful_restart=graceful_restart, rough_restart=rough_restart, logger=logger, greenlet_manager=greenlet_manager, *args, **kwargs)
        new_greenlet.link_value(callback=self.__graceful_termination)
        new_greenlet.link_exception(callback=self.__rough_termination)
        return new_greenlet

    def __try_restart(self, greenlet, check=False):
        if check:
            with ignored(AttributeError):
                greenlet.logger.info("Restarting greenlet '{func_name}'...".format(func_name=func_name))
            self.__restart_greenlet(greenlet=greenlet)
            return True
        return False

    def try_graceful_restart(self, greenlet):
        return self.__try_restart(greenlet=greenlet, check=greenlet.graceful_restartable)

    def try_rough_restart(self, greenlet):
        return self.__try_restart(greenlet=greenlet, check=greenlet.rough_restartable)

    def __restart_greenlet(self, greenlet):
        sleep(self.restart_sleep_interval)
        new_greenlet = self.spawn(run=greenlet._run,
            graceful_restart=greenlet.graceful_restart,
            rough_restart=greenlet.rough_restart,
            logger=greenlet.logger,
            greenlet_manager=greenlet.manager,
            *greenlet.rg_args,
            **greenlet.rg_kwargs)
        greenlet.manager._swap_greenlets(old_greenlet=greenlet, new_greenlet=new_greenlet)
        return new_greenlet

    def __graceful_termination(self, greenlet):
        if not greenlet.killed: #killed greenlets allowed to die but still tracked by manager
            if not self.try_graceful_restart(greenlet=greenlet):
                greenlet.manager._pop_greenlets(old_greenlet=greenlet)

    def __rough_termination(self, greenlet):
        if greenlet.killed: #killed greenlets allowed to die but still tracked by manager
            assert isinstance(greenlet.exception, KilledException)
        else:
            logger, func_name, error_msg = greenlet.logger, greenlet._run.__name__, greenlet.exception
            with ignored(AttributeError):
                logger.error("Greenlet '{func_name}' has encountered an uncaught error: {err}".format(func_name=func_name, err=error_msg))
            
            if not self.try_rough_restart(greenlet=greenlet):
                greenlet.manager._pop_greenlets(old_greenlet=greenlet)

    def killone(self, greenlet, block=True, *args, **kwargs):
        self.kill(greenlets=[greenlet], block=block)

    def kill(self, greenlets=None, block=True, *args, **kwargs):
        greenlets = self.greenlets if greenlets is None else greenlets
        for greenlet in greenlets:
            greenlet.killed = True
        killall(greenlets=greenlets, exception=KilledException, block=False)
        if block:
            joinall(greenlets=greenlets)

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

    __metaclass__ = RestartableGreenletMeta

    def __init__(self,
            run,
            greenlet_manager,
            logger=None,
            graceful_restart=True,
            rough_restart=True,
            *args,
            **kwargs):
        assert isinstance(greenlet_manager, AsyncContextManager)
        self.__manager = greenlet_manager
        self.__logger = logger
        self.__graceful_restart = graceful_restart
        self.__rough_restart = rough_restart
        self.__args = args
        self.__kwargs = kwargs
        self.killed = False
        super(RestartableGreenlet, self).__init__(run=run, *args, **kwargs)

    @property
    def killed(self):
        return self.__killed
    
    @killed.setter
    def killed(self, killed):
        self.__killed = bool(killed)

    @property
    def manager(self):
        return self.__manager

    @property
    def logger(self):
        return self.__manager

    @property
    def graceful_restart(self):
        return self.__graceful_restart

    @property
    def rough_restart(self):
        return self.__rough_restart

    @property
    def rg_args(self):
        return self.__args

    @property
    def rg_kwargs(self):
        return self.__kwargs

    @property
    def running(self):
        return self.started and not self.ready

    @property
    def stopped(self):
        return self.started and self.ready
    
    @property
    def stopped_rough(self):
        return self.stopped and not self.successful

    @property
    def stopped_graceful(self):
        return self.stopped and self.successful
    
    @property
    def rough_restartable(self):
        return self.stopped_rough and self.rough_restart and self.manager.is_running() and isinstance(self.exception, Exception) and not isinstance(self.exception, KilledException)
    
    @property
    def graceful_restartable(self):
        return self.stopped_graceful and self.graceful_restart and self.manager.is_running() and self.exception is None
    
    @property
    def restartable(self):
        return self.rough_restartable or self.graceful_restartable
    
    def _report_error(self, exc_info, *args, **kwargs):
        #suppress stdout/stderr for KilledExceptions
        if isinstance(exc_info[1], KilledException):
            with RedirectStdStreams():
                value = super(RestartableGreenlet, self)._report_error(exc_info=exc_info, *args, **kwargs)
            return value
        return super(RestartableGreenlet, self)._report_error(exc_info=exc_info, *args, **kwargs)

    def kill(self, exception=None, block=True, *args, **kwargs):
        greenlets = [self]
        killall(greenlets=greenlets, exception=KilledException, block=False)
        if block:
            joinall(greenlets=greenlets)

class AsyncContextManager(object):
    __async_class = gevent.event.Event

    __metaclass__ = AsyncContextManagerMeta

    def __init__(self, *args, **kwargs):
        self.__stopped = AsyncContextManager.__async_class()
        self.__stopped.set()
        self.__sub_greenlets = []

    @property
    def greenlets(self):
        return self.__sub_greenlets
    
    def __new__(cls, async_hidden_key=None, *args, **kwargs):
        instance = super(AsyncContextManager, cls).__new__(cls)
        instance.__async_hidden_key = uuid().get_hex() if async_hidden_key is None else async_hidden_key
        instance.__running = AsyncContextManager.__async_class()
        instance.__running.clear()
        get_async_manager().add_context_manager(key=instance.__async_hidden_key, manager=instance)
        return instance

    def __del__(self, *args, **kwargs):
        get_async_manager().remove_context_manager(key=self.__async_hidden_key, manager=self)

    def __enter__(self, *args, **kwargs):
        self.__running.set()
        self.__stopped.clear()
        self.__respawn_stopped_greenlets()
        if hasattr(self, "start"): self.start(*args, **kwargs)

    def __exit__(self, *args, **kwargs):
        self.__kill_running_greenlets()
        self.__running.clear()
        if hasattr(self, "stop"): self.stop(*args, **kwargs)

    def __respawn_stopped_greenlets(self):
        for greenlet in self.__sub_greenlets[:]: #needs to be copy as list is being edited
            if greenlet.restartable:
                get_restart_pool().restart_greenlet(greenlet=greenlet) # new greenlet readded to sub_greenlets through pool

    def __kill_running_greenlets(self):
        get_restart_pool().kill(greenlets=self.__sub_greenlets)

    #wraps new greenlets
    def __force_running(self, forced_func, *args, **kwargs):
        self.wait_for_running()
        forced_func(*args, **kwargs)

    #intended to be used by RestartPool
    def _swap_greenlets(self, old_greenlet, new_greenlet):
        self.pop_greenlets(old_greenlet=old_greenlet)
        if not new_greenlet in self.__sub_greenlets: self.__sub_greenlets.append(new_greenlet)

    #intended to be used by RestartPool
    def _pop_greenlets(self, old_greenlet):
        with ignored(ValueError):
            self.__sub_greenlets.remove(old_greenlet)

    def spawn_greenlet(self, run, *args, **kwargs):
        greenlet = get_restart_pool().spawn(run=self.__force_running, manager=self, forced_func=run, *args, **kwargs)
        self.__sub_greenlets.append(greenlet)
        return greenlet

    def is_running(self):
        return self.__running.is_set()

    def is_stopping(self):
        return self.__stopped.is_set()

    def wait_for_running(self):
        self.__running.wait()

    def wait_for_stop(self):
        self.__stopped.wait()

    def trigger_stop(self):
        self.__stopped.set()