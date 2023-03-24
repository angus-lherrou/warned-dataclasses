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

import functools
import inspect
import warnings
from dataclasses import Field
from typing import Protocol, ClassVar, Dict, Type, get_type_hints, cast, Set, Tuple

from typing_extensions import TypeAlias, Annotated as Warned

from .common import (
    CONDITION_CLASS,
    ConditionalParameterError,
    ConditionalParameterWarning,
)


class DeferredWarning:
    def __init__(
        self,
        cond: CONDITION_CLASS,
        message: str,
        error: bool,
        satisfy_on_warn: bool,
    ):
        self.cond = cond
        self.satisfied = False
        self.error = error
        self.satisfy_on_warn = satisfy_on_warn
        self.message = message

    def satisfy_warning(self):
        self.satisfied = True

    def invoke_warning(self):
        if not self.satisfied:
            if self.satisfy_on_warn:
                self.satisfy_warning()
            if self.error:
                raise ConditionalParameterError(self.message)
            else:
                warnings.warn(self.message, ConditionalParameterWarning)


AnnotatedAlias: TypeAlias = type(Warned[None, None])  # type: ignore


class DeferredWarningFactory:
    def __init__(
        self,
        cond: CONDITION_CLASS,
        message: str,
        error: bool,
        satisfy_on_warn: bool,
    ):
        self.cond = cond
        self.message = message
        self.error = error
        self.satisfy_on_warn = satisfy_on_warn

    def generate(self):
        return DeferredWarning(
            self.cond, self.message, self.error, self.satisfy_on_warn
        )


class Dataclass(Protocol):
    __dataclass_fields__: ClassVar[Dict[str, Field]]
    __dataclass_params__: ClassVar


class WarnedDataclass(Protocol):
    __dataclass_fields__: ClassVar[Dict[str, Field]]
    __dataclass_params__: ClassVar
    __deferred_warnings__: Dict[CONDITION_CLASS, Dict[str, DeferredWarning]]


def patch_init_method(
    cls,
    warnings: Dict[CONDITION_CLASS, Dict[str, DeferredWarningFactory]],
) -> Type[WarnedDataclass]:
    # cls = cast(Type[_WarnedDataclass], cls)
    # cls.__inner_init__ = cls.__init__  # type: ignore

    @functools.wraps(cls, updated=())
    class WarnedClass(cls):  # type: ignore
        def __init__(self, *args, **kwargs):
            super(WarnedClass, self).__init__(*args, **kwargs)

            type_hints = get_type_hints(self, include_extras=True)

            bound_arguments = inspect.signature(super(WarnedClass, self).__init__).bind(
                *args, **kwargs
            )

            self.__deferred_warnings__ = {
                cond: {name: factory.generate() for name, factory in factories.items()}
                for cond, factories in warnings.items()
            }

            # satisfy warnings for implicit attributes
            for name, field_obj in self.__dataclass_fields__.items():
                if not field_obj.init:
                    # not an init parameter; ignore
                    continue

                if name in bound_arguments.arguments:
                    # explicit value was passed; leave unsatisfied
                    continue

                if not isinstance(type_hints[name], AnnotatedAlias):
                    # not Annotated; ignore
                    continue

                cond = type_hints[name].__metadata__[0]
                if not isinstance(cond, CONDITION_CLASS):
                    # not our usage of Annotated
                    continue

                # no explicit value passed; satisfy warning
                self.__deferred_warnings__[cond][name].satisfy_warning()

    return WarnedClass


def _collect_warnings(obj, cond: CONDITION_CLASS, exists=True):
    errors = []
    warnings = cast(WarnedDataclass, obj).__deferred_warnings__
    if cond not in warnings:
        if exists:
            raise ValueError(f"Condition {cond} not present for {obj}")
    else:
        for warning in warnings[cond].values():
            try:
                warning.invoke_warning()
            except ConditionalParameterError as cpe:
                errors.append(cpe)
    return errors


def _collect_all_warnings(obj):
    errors = []
    for warned_attrs in cast(WarnedDataclass, obj).__deferred_warnings__.values():
        for warning in warned_attrs.values():
            try:
                warning.invoke_warning()
            except ConditionalParameterError as cpe:
                errors.append(cpe)
    return errors


def _collect_conditions(dclses: Tuple[WarnedDataclass, ...]) -> Set[CONDITION_CLASS]:
    return {cond for dcls in dclses for cond in dcls.__deferred_warnings__.keys()}


def _satisfy(obj, cond: CONDITION_CLASS, exists=True):
    warnings = cast(WarnedDataclass, obj).__deferred_warnings__
    if cond not in warnings:
        if exists:
            raise ValueError(f"Condition {cond} not present for {obj}")
    else:
        for warning in cast(WarnedDataclass, obj).__deferred_warnings__[cond].values():
            warning.satisfy_warning()
