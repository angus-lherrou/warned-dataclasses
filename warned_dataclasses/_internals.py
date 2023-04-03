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
from dataclasses import MISSING, Field
from types import GenericAlias
from typing import (
    ClassVar,
    Dict,
    Protocol,
    Set,
    Tuple,
    Type,
    cast,
    get_type_hints,
    List,
)

from typing_extensions import Annotated as Warned
from typing_extensions import TypeAlias

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
    __warning_factories__: ClassVar[
        Dict[CONDITION_CLASS, Dict[str, DeferredWarningFactory]]
    ]
    __deferred_warnings__: Dict[CONDITION_CLASS, Dict[str, DeferredWarning]]


def is_warned_dataclass(obj):
    """Returns True if obj is a warned dataclass or an instance of a
    dataclass."""
    cls = (
        obj
        if isinstance(obj, type) and not isinstance(obj, GenericAlias)
        else type(obj)
    )
    return hasattr(cls, "__warning_factories__")


def undupe_mro(mro: List[Type]):
    unduped_mro = [mro[0]]

    for i in range(1, len(mro)):
        prev_cls = mro[i - 1]
        curr_cls = mro[i]

        if (
            prev_cls.__name__ == "WarnedClass" or prev_cls.__name__ == curr_cls.__name__
        ) and hasattr(prev_cls, "__warning_factories__"):
            # classes with same name, lower one has __warning_factories__;
            # therefore upper one is the unpatched class; remove from MRO
            continue
        unduped_mro.append(curr_cls)
    return tuple(unduped_mro)


def patch_init_method(
    cls,
    warning_factories: Dict[CONDITION_CLASS, Dict[str, DeferredWarningFactory]],
    warn_on_default: bool,
) -> Type[WarnedDataclass]:
    @functools.wraps(cls, updated=())
    class WarnedClass(cls):  # type: ignore
        __warning_factories__: Dict[
            CONDITION_CLASS, Dict[str, DeferredWarningFactory]
        ] = warning_factories

        # @functools.wraps(cls.__init__)
        def __init__(self, *args, **kwargs):
            super(WarnedClass, self).__init__(*args, **kwargs)
            type_hints = get_type_hints(type(self), include_extras=True)

            bound_arguments = inspect.signature(super(WarnedClass, self).__init__).bind(
                *args, **kwargs
            )

            all_warning_factories = [
                cls_.__warning_factories__
                for cls_ in undupe_mro(type(self).mro())
                if is_warned_dataclass(cls_)
            ]

            self.__deferred_warnings__ = {
                cond: {name: factory.generate() for name, factory in factories.items()}
                for wfs in all_warning_factories
                for cond, factories in wfs.items()
            }

            # satisfy warnings for implicit attributes
            for name, field_obj in self.__dataclass_fields__.items():
                if not field_obj.init:
                    # not an init parameter; leave warning in-place
                    continue

                if name in bound_arguments.arguments:
                    # explicit value was passed
                    if warn_on_default:
                        # warn on any explicit value, including equal to default
                        continue
                    else:
                        if field_obj.default is field_obj.default_factory is MISSING:
                            # no default set; unlikely use case but should
                            # account for it; leave warning in place
                            continue
                        elif (
                            MISSING
                            is not field_obj.default
                            != bound_arguments.arguments[name]
                        ):
                            # non-default value was passed; warn
                            continue
                        elif field_obj.default_factory is not MISSING:
                            # default_factory set and value was passed
                            warnings.warn(
                                f"default_factory was overridden for {name}. Assuming "
                                f"{field_obj.default_factory} is a pure function that "
                                f"returns a value with a reasonable __eq__."
                            )
                            default_value = field_obj.default_factory()
                            if default_value != bound_arguments.arguments[name]:
                                # non-default value was passed; warn
                                continue
                        # else: default value was passed

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
