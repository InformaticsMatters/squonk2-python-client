"""Python utilities common to UI, DM and AS.
"""

import copy
from dataclasses import dataclass
from typing import Any

from munch import DefaultMunch

# An object to return in DefaultMunch objects
_UNDEFINED: object = object()


@dataclass
class ApiRv:
    """The return value from most of the the AsApi class public methods.

    :param success: True if the call was successful, False otherwise.
    :param msg: API request response content
    :param defaultmunch_msg: A DefaultMunch representation of the msg
    :param http_status_code: An HTTPS status code (0 if not available)
    """

    success: bool
    msg: dict[Any, Any]
    defaultmunch_msg: DefaultMunch
    http_status_code: int = 0

    def __init__(self, success: bool, msg: dict[Any, Any], http_status_code: int = 0):
        assert isinstance(msg, dict)
        self.success = success
        self.http_status_code = http_status_code
        self.msg = copy.deepcopy(msg)
        self.defaultmunch_msg = DefaultMunch.fromDict(msg, _UNDEFINED)
