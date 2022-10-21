#  Copyright 2022 Angus L'Herrou Dawson.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import logging
from dataclasses import Field, MISSING
# sorry, PyCharm stubs! sorry, dataclasses devs!
from dataclasses import _process_class, _FIELDS

from typing import Dict, List, Callable, Optional

from collections import defaultdict


class DeferredWarning:
    def __init__(
        self, condition: str, deferred_message: Callable[[str], str], error=False
    ):
        print("initialized")
        self.condition = condition
        self.deferred_message = deferred_message
        self.satisfied = False
        self.error = error
        self.message = None

    def satisfy(self):
        self.satisfied = True

    def supply_parameter(self, param: str):
        self.message = self.deferred_message(param)

    def invoke(self):
        if not self.satisfied:
            if self.message is None:
                raise ValueError("didn't supply parameter!")
            if self.error:
                raise ConditionalParameterError(self.message)
            else:
                logger.warning(self.message)


#: The dictionary of deferred warnings, from the name of
#: a condition to the list of deferred warnings.
DEFERRED_WARNINGS: Dict[str, List[DeferredWarning]] = defaultdict(list)


logger = logging.getLogger(__name__)


class ConditionalParameterError(Exception):
    pass


def satisfy(key: str) -> None:
    """
    Satisfies all deferred warnings for a given key.

    :param key: the name of the condition
    :return: None
    """
    if key not in DEFERRED_WARNINGS:
        raise KeyError(
            f'Condition "{key}" has not been declared and could not be disarmed.'
        )
    for deferred_warning in DEFERRED_WARNINGS[key]:
        deferred_warning.satisfy()


def invoke(key: str) -> None:
    """
    Invokes all armed deferred warnings for a given condition.

    :param str key: the name of the condition
    :return: None
    """
    if key not in DEFERRED_WARNINGS:
        raise KeyError(
            f'Condition "{key}" has not been declared and could not be invoked'
        )
    for deferred_warning in DEFERRED_WARNINGS[key]:
        deferred_warning.invoke()


def invoke_all() -> None:
    """
    Invokes all armed deferred warnings for all conditions.

    :return: None
    """
    for key in DEFERRED_WARNINGS:
        invoke(key)


"""
dataclasses drop-in replacements here
"""


def dataclass(
    cls=None,
    /,
    *,
    init=True,
    repr=True,
    eq=True,
    order=False,
    unsafe_hash=False,
    frozen=False,
):
    """Returns the same class as was passed in, with dunder methods
    added based on the fields defined in the class.

    Examines PEP 526 __annotations__ to determine fields.

    If init is true, an __init__() method is added to the class. If
    repr is true, a __repr__() method is added. If order is true, rich
    comparison dunder methods are added. If unsafe_hash is true, a
    __hash__() method function is added. If frozen is true, fields may
    not be assigned to after instance creation.
    """

    def wrap(cls):
        return _warned_process_class(cls, init, repr, eq, order, unsafe_hash, frozen)

    # See if we're being called as @dataclass or @dataclass().
    if cls is None:
        # We're called with parens.
        return wrap

    # We're called as @dataclass without parens.
    return wrap(cls)


def _warned_process_class(cls, init, repr, eq, order, unsafe_hash, frozen):
    cls = _process_class(cls, init, repr, eq, order, unsafe_hash, frozen)
    for field in getattr(cls, _FIELDS):
        deferred_warning: DeferredWarning = field._deferred_warning
        deferred_warning.supply_parameter(field.name)
        DEFERRED_WARNINGS[deferred_warning.condition].append(deferred_warning)


class WarnedField(Field):
    __slots__ = (
        *Field.__slots__,
        "_deferred_warning",
    )

    def __init__(self, deferred_warning: DeferredWarning, *args, **kwargs):
        super(WarnedField, self).__init__(*args, **kwargs)
        self._deferred_warning = deferred_warning


def field(
    *,
    condition: Optional[str] = None,
    error_on_invoke: bool = False,
    default=MISSING,
    default_factory=MISSING,
    init=True,
    repr=True,
    hash=None,
    compare=True,
    metadata=None,
):

    if condition is not None:
        deferred_warning = DeferredWarning(
            condition,
            lambda parameter: (
                f"Value provided for --{parameter} but "
                f'required condition "{condition}" not met.'
            ),
            error=error_on_invoke,
        )
    else:
        deferred_warning = None

    # Code below this line is to be kept in sync with Python's dataclasses code
    if default is not MISSING and default_factory is not MISSING:
        raise ValueError("cannot specify both default and default_factory")
    return WarnedField(
        deferred_warning, default, default_factory, init, repr, hash, compare, metadata
    )
