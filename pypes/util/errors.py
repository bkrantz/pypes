#!/usr/bin/env python

from pypes import import_restriction

__all__ = []

if __name__.startswith(import_restriction):
    __all__ += [
        "PypesException",
        "QueueEmpty",
        "QueueFull",
        "QueueConnected",
        "SetupError",
        "ReservedName",
        "ActorInitFailure",
        "InvalidEventConversion",
        "InvalidEventDataModification",
        "InvalidEventModification",
        "InvalidActorOutput",
        "InvalidActorInput",
        "ResourceNotModified",
        "MalformedEventData",
        "UnauthorizedEvent",
        "ForbiddenEvent",
        "ResourceNotFound",
        "EventCommandNotAllowed",
        "ActorTimeout",
        "ResourceConflict",
        "ResourceGone",
        "UnprocessableEventData",
        "EventRateExceeded",
        "ServiceUnavailable",
        "EventAttributeError"
    ]

class PypesException(Exception):

    def __init__(self, message="", **kwargs):
        super(PypesException, self).__init__()
        if not isinstance(message, list):
            message = [message]
        self.message = message
        self.__dict__.update(kwargs)

class QueueEmpty(PypesException):
    pass

class QueueFull(PypesException):
    def __init__(self, queue=None, **kwargs):
        self.queue = queue
        super(QueueFull, self).__init__(**kwargs)

class QueueConnected(PypesException):
    pass


class SetupError(PypesException):
    pass


class ReservedName(PypesException):
    pass


class ActorInitFailure(PypesException):
    """**A specific Actor initialization failed**"""
    pass


class InvalidEventConversion(PypesException):
    """**An attempt to convert Event or an Event subclass to a different class was impossible**"""
    pass


class InvalidEventDataModification(PypesException):
    """**An attempt to modify Event.data to an invalid format for the Event subclass occurred**"""
    pass

class InvalidEventModification(PypesException):
    pass


class InvalidActorOutput(PypesException):
    """**An Actor sent an event that was not defined as a valid output Event class**"""
    pass


class InvalidActorInput(PypesException):
    """**An Actor received an event that was not defined as a valid input Event class**"""
    pass


class ResourceNotModified(PypesException):
    """**An Actor attempted to modify an external persistent entity, but that modification was not successful**"""
    pass


class MalformedEventData(PypesException):
    """**Event data was malformed for a particular Actor to work on it**"""
    pass


class UnauthorizedEvent(PypesException):
    """**Event either did not contain credentials for a restricted actor, or contained invalid credentials**"""
    pass


class ForbiddenEvent(PypesException):
    """**Event was authenticated properly for a given Actor, but the credentials were not granted permissions for the requested action**"""
    pass


class ResourceNotFound(PypesException):
    """**A specific queue was requested on an Actor, but that queue was not defined or connected for that actor**"""
    pass


class EventCommandNotAllowed(PypesException):
    """**A semantic property on an incoming event that modified actor behavior was not implemented**"""
    pass


class ActorTimeout(PypesException):
    """**An Actor timed out the requested work on an incoming event**"""
    pass


class ResourceConflict(PypesException):
    """**An event attempted to draw upon a persistant storage resource that is no longer available**"""
    pass


class ResourceGone(PypesException):
    """**An event attempted to draw upon a persistant storage resource that is no longer available**"""
    pass


class UnprocessableEventData(PypesException):
    """**Event data was well formed, but unprocessable for application logic semantic purposes**"""
    pass


class EventRateExceeded(PypesException):
    """**The allowed event rate for a given actor has been exceeded**"""
    pass


class ServiceUnavailable(PypesException):
    """**A defined Event.service was requested but that particular service was not found**"""
    pass


class EventAttributeError(PypesException):
    """**An event attribute necessary to the proper processing of the event was missing**"""
    pass