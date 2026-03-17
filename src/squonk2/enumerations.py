"""Enumerations, available to AS, DM and UI."""

from enum import Enum


class EventStreamFormat(Enum):
    """Enumeration of EventStream formats"""

    JSON_STRING = 1
    PROTOCOL_STRING = 2


class ScopeEnum(Enum):
    """Enumeration of Scopes"""

    USER = 1
    PRODUCT = 2
    UNIT = 3
    ORGANISATION = 4
    GLOBAL = 5


class DefaultProductPrivacyEnum(Enum):
    """Enumeration of Default product Privacy"""

    ALWAYS_PRIVATE = 1
    ALWAYS_PUBLIC = 2
    DEFAULT_PRIVATE = 3
    DEFAULT_PUBLIC = 4
