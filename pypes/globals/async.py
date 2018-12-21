
DEFAULT_SLEEP_INTERVAL = 0.001

__async_manager = None
__restart_pool = None

def get_async_manager():
    global __async_manager
    if __async_manager is None:
        from pypes.util.async import AsyncManager
        __async_manager = AsyncManager()
    return __async_manager

#should only be used for testing
def _override_async_manager(manager):
    global __async_manager
    if not __async_manager is None:
        #__async_manager.__exit__()
        __async_manager.__del__()
    __async_manager = manager

#should only be used for testing
def _override_restart_pool(pool):
    global __restart_pool
    if not __restart_pool is None:
        from gevent.greenlet import killall
        killall(greenlets=list(__restart_pool.greenlets), block=True)
    __restart_pool = pool

def get_restart_pool():
    global __restart_pool
    if __restart_pool is None:
        from pypes.util.async import RestartPool
        __restart_pool = RestartPool(restart_sleep_interval=1)
    return __restart_pool