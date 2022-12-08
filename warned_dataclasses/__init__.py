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

import inspect
import logging
import sys

from collections import defaultdict
from typing import (
    Callable,
    Protocol,
    get_type_hints,
    Type,
    overload,
    Union,
    cast,
    Optional,
    ClassVar,
    TypeVar,
)
from dataclasses import Field, is_dataclass

if sys.version_info >= (3, 9):
    from typing import Annotated as Warned
else:
    from typing_extensions import Annotated as Warned

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

logger = logging.getLogger(__name__)

_AnnotatedAlias: TypeAlias = type(Warned[None, None])  # type: ignore


__all__ = ["ConditionalParameterError", "Warned", "satisfy", "invoke", "warned"]


class ConditionalParameterError(Exception):
    pass


class _DeferredWarningFactory:
    def __init__(
        self,
        condition: str,
        message: str,
        error=False,
    ):
        self.condition = condition
        self.message = message
        self.error = error

    def generate(self):
        return _DeferredWarning(self.condition, self.message, self.error)


class _DeferredWarning:
    def __init__(
        self,
        condition: str,
        message: str,
        error=False,
    ):
        self.condition = condition
        self.satisfied = False
        self.error = error
        self.message = message

    def satisfy(self):
        self.satisfied = True

    def invoke(self):
        if not self.satisfied:
            if self.error:
                raise ConditionalParameterError(self.message)
            else:
                logger.warning(self.message)


class _Dataclass(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Field]]
    __dataclass_params__: ClassVar


class _WarnedDataclass(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Field]]
    __dataclass_params__: ClassVar
    __deferred_warnings__: dict[str, dict[str, _DeferredWarning]]

    def __inner_init__(self, *args, **kwargs) -> None:
        ...


def _patch_init_method(
    cls, warnings: dict[str, dict[str, _DeferredWarningFactory]]
) -> Type[_WarnedDataclass]:
    cls = cast(Type[_WarnedDataclass], cls)
    cls.__inner_init__ = cls.__init__  # type: ignore

    def __init__(self_: _WarnedDataclass, *args, **kwargs):
        self_.__deferred_warnings__ = {
            condition: {name: factory.generate() for name, factory in factories.items()}
            for condition, factories in warnings.items()
        }

        type_hints = get_type_hints(self_, include_extras=True)

        bound_arguments = inspect.signature(self_.__inner_init__).bind(*args, **kwargs)

        for name, field_obj in self_.__dataclass_fields__.items():
            if not field_obj.init:
                # not an init parameter; ignore
                continue
            if not isinstance(type_hints[name], _AnnotatedAlias):
                # not Annotated; ignore
                continue

            if name not in bound_arguments.arguments:
                # no explicit value passed; satisfy warning
                condition: str = type_hints[name].__metadata__[0]
                self_.__deferred_warnings__[condition][name].satisfy()
            # else: leave warning unsatisfied

        self_.__inner_init__(*args, **kwargs)

    __init__.__doc__ = cls.__init__.__doc__
    __init__.__annotations__ = cls.__init__.__annotations__

    cls.__init__ = __init__  # type: ignore

    return cls


_T = TypeVar("_T")


@overload
def warned(
    cls: Type[_T],
    /,
) -> Type[_T]:
    ...


@overload
def warned(
    *,
    error_on_invoke: bool = False,
) -> Callable[[Type[_T]], Type[_T]]:
    ...


def warned(
    cls: Optional[Type[_T]] = None,
    /,
    *,
    error_on_invoke: bool = False,
) -> Union[Type[_T], Callable[[Type[_T]], Type[_T]]]:
    def generate_warnings(cls_: Type[_T]) -> Type[_T]:
        if not is_dataclass(cls_):
            raise ValueError("@warned should only be used with a dataclass.")

        cls_annotations = cls_.__annotations__

        warnings: dict[str, dict[str, _DeferredWarningFactory]] = defaultdict(dict)

        for name, annotation in cls_annotations.items():
            if not isinstance(annotation, _AnnotatedAlias):
                continue
            # add to triggers
            condition: str = annotation.__metadata__[0]
            warning = _DeferredWarningFactory(
                condition,
                (
                    f'a value was provided for the attribute "{name}" but '
                    f'the required condition "{condition}" was not met.'
                ),
                error_on_invoke,
            )
            warnings[condition][name] = warning

        return cast(
            Type[_T], _patch_init_method(cast(Type[_Dataclass], cls_), warnings)
        )

    if cls is None:
        # invoked as @warned()
        return generate_warnings
    # invoked as @warned
    return generate_warnings(cls)


def satisfy(obj, condition: str):
    for warning in (
        cast(_WarnedDataclass, obj).__deferred_warnings__[condition].values()
    ):
        warning.satisfy()


def invoke(obj, condition: str):
    for warning in (
        cast(_WarnedDataclass, obj).__deferred_warnings__[condition].values()
    ):
        warning.invoke()
