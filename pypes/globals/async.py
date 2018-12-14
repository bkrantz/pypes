
__async_manager = None
__restart_pool = None

def get_async_manager():
    global __async_manager
    if __async_manager is None:
        from pypes.util.async import AsyncManager
        __async_manager = AsyncManager()
    return __async_manager

def get_restart_pool():
    global __restart_pool
    if __restart_pool is None:
        from pypes.util.async import RestartPool
        __restart_pool = RestartPool(sleep_interval=1)
    return __restart_pool