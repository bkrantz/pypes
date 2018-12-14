from pypes import import_restriction

__all__ = []

if __name__.startswith(import_restriction):
    __all__ += [
        "TimeTracker"
    ]

def TimeTracker(actor_clazz):
    old_init = actor_clazz.__init__
    old_consume_wrapper = actor_clazz._Actor__consume_wrapper
    old_create_event = actor_clazz.create_event

    def new_init(self, name, new_event_timeout=0, *args, **kwargs):
        old_init(self, name, *args, **kwargs)
        self.new_event_timeout = new_event_timeout

    def new_consume_wrapper(self, event, *args, **kwargs):
        event.set_started(actor_name=self.name)
        event, queues = old_consume_wrapper(self, event, *args, **kwargs)
        if not event is None:
            event.set_ended(actor_name=self.name)
        return event, queues

    def new_create_event(self, *args, **kwargs):
        event = old_create_event(self, *args, **kwargs)
        event.timeout = self.new_event_timeout
        return event

    actor_clazz.__init__ = new_init
    actor_clazz._Actor__consume_wrapper = new_consume_wrapper
    actor_clazz.create_event = new_create_event
    return actor_clazz