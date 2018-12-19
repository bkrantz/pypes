#!/usr/bin/env python

import collections

from pypes.util.errors import (ResourceNotModified, MalformedEventData, InvalidEventDataModification, InvalidEventModification,
    UnauthorizedEvent, ForbiddenEvent, ResourceNotFound, EventCommandNotAllowed, ActorTimeout, ResourceConflict,
    ResourceGone, UnprocessableEventData, EventRateExceeded, PypesException, ServiceUnavailable)
from pypes import import_restriction
from pypes.util.event import EventManager
__all__ = []

if __name__.startswith(import_restriction):
    __all__ += [
        "DEFAULT_SERVICE",
        "DEFAULT_STATUS_CODE",
        "DEFAULT_LOG_FILENAME",
        "HTTPStatusMap",
        "HTTPStatuses",
        "get_event_manager"
    ]

DEFAULT_SERVICE = "default"
DEFAULT_STATUS_CODE = 200
DEFAULT_LOG_FILENAME = "compysition.log"

HTTPStatusMap = collections.defaultdict(lambda: {"status": 500},
    {
        ResourceNotModified:            {"status": 304},
        MalformedEventData:             {"status": 400},
        InvalidEventModification:       {"status": 400},
        UnauthorizedEvent:              {"status": 401,
            "headers": {'WWW-Authenticate': 'Basic realm="Compysition Server"'}},
        ForbiddenEvent:                 {"status": 403},
        ResourceNotFound:               {"status": 404},
        EventCommandNotAllowed:         {"status": 405},
        ActorTimeout:                   {"status": 408},
        ResourceConflict:               {"status": 409},
        ResourceGone:                   {"status": 410},
        UnprocessableEventData:         {"status": 422},
        EventRateExceeded:              {"status": 429},
        PypesException:                 {"status": 500},
        ServiceUnavailable:             {"status": 503},
        type(None):                     {"status": 200}
    })

HTTPStatuses = {
    200: "OK",
    201: "Created",
    202: "Accepted",
    204: "No Content",
    205: "Reset Content",
    206: "Partial Content",
    304: "Not Modified",
    400: "Bad Request",
    401: "Unauthorized",
    402: "Payment Required",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    408: "Request Timeout",
    409: "Conflict",
    410: "Gone",
    411: "Length Required",
    415: "Unsupported Media Type",
    422: "Unprocessable Entity",
    423: "Locked",
    429: "Too Many Requests",
    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
    508: "Loop Detected",
}

__event_manager = None

def get_event_manager():
    global __event_manager
    if __event_manager is None:
        __event_manager = EventManager()
    return __event_manager