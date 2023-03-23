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

import sys

from collections import defaultdict
from dataclasses import is_dataclass
from typing import (
    Callable,
    overload,
    Union,
    Optional,
    TypeVar,
    List,
    Generic,
)

from ._internals import (
    _collect_warnings,
    _collect_conditions,
    _collect_all_warnings,
    _satisfy,
)

if sys.version_info >= (3, 9):
    pass
else:
    pass

from ._internals import *

_T = TypeVar("_T")


class ConditionSet(Generic[_T]):
    def __init__(self, *dclses: _T):
        for dcls in dclses:
            if not is_dataclass(dcls) and not hasattr(dcls, "__deferred_warnings__"):
                raise ValueError(
                    "ConditionSet should only be used with dataclass objects."
                )

        self.objects: Tuple[WarnedDataclass, ...] = cast(
            Tuple[WarnedDataclass, ...], dclses
        )
        self.conditions: Set[CONDITION_CLASS] = _collect_conditions(self.objects)

    def _collect_warnings(
        self, condition: CONDITION_CLASS
    ) -> List["ConditionalParameterError"]:
        errs = []
        for obj in self.objects:
            errs.extend(_collect_warnings(obj, condition, exists=False))
        return errs

    def satisfy(self, condition: CONDITION_CLASS):
        if condition not in self.conditions:
            raise ValueError(f"Condition {condition} not present for {self}")
        for obj in self.objects:
            _satisfy(obj, condition, exists=False)

    def warn_for_condition(self, condition: CONDITION_CLASS):
        if condition not in self.conditions:
            raise ValueError(f"Condition {condition} not present for {self}")
        errs = self._collect_warnings(condition)
        if errs:
            raise ConditionalParameterError.from_list(errs)

    def warn_all(self):
        errs = []
        for cond in self.conditions:
            errs.extend(self._collect_warnings(cond))
        if errs:
            raise ConditionalParameterError.from_list(errs)


@overload
def warned(
    cls: Type[_T],
    /,
) -> Type[_T]:
    ...


@overload
def warned(
    *,
    error: bool = False,
    satisfy_on_warn: bool = True,
) -> Callable[[Type[_T]], Type[_T]]:
    ...


def warned(
    cls: Optional[Type[_T]] = None,
    /,
    *,
    error: bool = False,
    satisfy_on_warn: bool = True,
) -> Union[Type[_T], Callable[[Type[_T]], Type[_T]]]:
    def generate_warnings(cls_: Type[_T]) -> Type[_T]:
        if not is_dataclass(cls_):
            raise ValueError("@warned should only be used with a dataclass.")

        cls_annotations = cls_.__annotations__

        warnings: Dict[
            CONDITION_CLASS, Dict[str, DeferredWarningFactory]
        ] = defaultdict(dict)

        for name, annotation in cls_annotations.items():
            if not isinstance(annotation, AnnotatedAlias):
                continue

            cond = annotation.__metadata__[0]
            if not isinstance(cond, CONDITION_CLASS):
                # not our usage of Annotated
                continue

            # add to triggers
            warning = DeferredWarningFactory(
                cond,
                (
                    f'a value was provided for the attribute "{name}" but '
                    f'the required condition "{cond}" was not met.'
                ),
                error,
                satisfy_on_warn,
            )
            warnings[cond][name] = warning

        new_cls = cast(
            Type[_T],
            patch_init_method(cast(Type[Dataclass], cls_), warnings),
        )

        return new_cls

    if cls is None:
        # invoked as @warned()
        return generate_warnings
    # invoked as @warned
    return generate_warnings(cls)


def satisfy(obj, cond: CONDITION_CLASS):
    if isinstance(obj, ConditionSet):
        obj.satisfy(cond)
    else:
        _satisfy(obj, cond)


def warn_for_condition(obj, cond: CONDITION_CLASS):
    if isinstance(obj, ConditionSet):
        obj.warn_for_condition(cond)
    else:
        errors = _collect_warnings(obj, cond)
        if errors:
            raise ConditionalParameterError.from_list(errors)


def warn_all(obj):
    if isinstance(obj, ConditionSet):
        obj.warn_all()
    else:
        errors = _collect_all_warnings(obj)
        if errors:
            raise ConditionalParameterError.from_list(errors)
