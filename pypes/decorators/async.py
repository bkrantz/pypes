#!/usr/bin/env python
'''

from uuid import uuid4 as uuid
from gevent import event, sleep
import gevent
import signal

from pypes.util.async import AsyncManager, RestartPool
from pypes.globals.async import get_async_manager, get_restart_pool
from pypes import import_restriction

__all__ = []

if __name__.startswith(import_restriction):
    __all__ += [
        "GlobalAsyncManager",
        "AsyncContextManager"
    ]



def AsyncContextManager(clazz):

    _async_class = gevent.event.Event

    old_init = getattr(clazz, "__init__", None)
    old_start = getattr(clazz, "start", None)
    old_stop = getattr(clazz, "stop", None)
    old_enter = getattr(clazz, "__enter__", None)
    old_exit = getattr(clazz, "__exit__", None)
    old_spawn_thread = getattr(clazz, "spawn_thread", None)
    old_block = getattr(clazz, "block", None)
    old_is_running = getattr(clazz, "is_running", None)
    old_sleep = getattr(clazz, "sleep", None)
    old_wait = getattr(clazz, "wait", None)

    def new_init(self, *args, **kwargs):
        self.__async_hidden_key = uuid().get_hex()
        self.__running = _async_class()
        self.__block = _async_class()
        self.__running.clear()
        self.__block.clear()
        if not old_init is None:
            old_init(self, *args, **kwargs)

    def new_start(self, *args, **kwargs):
        value = None
        if not old_start is None:
            value = old_start(self, *args, **kwargs)
        self.__running.set()
        self.__block.clear()
        get_async_manager().add_context_manager(key=self.__async_hidden_key, obj=self)
        return value

    def new_stop(self, *args, **kwargs):
        self.__running.clear()
        self.__block.set()
        get_async_manager().remove_context_manager(key=self.__async_hidden_key)
        if not old_stop is None:
            return old_stop(self, *args, **kwargs)

    def new_enter(self, *args, **kwargs):
        return self.start(*args, **kwargs)

    def new_exit(self, *args, **kwargs):
        return self.stop(*args, **kwargs)

    def new_spawn_thread(self, *args, **kwargs):
        return get_restart_pool().spawn(*args, **kwargs)

    def new_block(self, *args, **kwargs):
        return self.__block.wait()

    def new_is_running(self, *args, **kwargs):
        return self.__running.is_set()

    def new_sleep(self, duration=0, *args, **kwargs):
        gevent.sleep(duration)

    def new_wait(self, *args, **kwargs):
        self.__running.wait()

    clazz.__init__ = new_init
    clazz.start = new_start
    clazz.stop = new_stop
    clazz.__enter__ = new_enter
    clazz.__exit__ = new_exit
    clazz.spawn_thread = new_spawn_thread
    clazz.block = new_block
    clazz.is_running = new_is_running
    clazz.sleep = new_sleep
    clazz.wait = new_wait

    return clazz
'''