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
import io
import warnings
from dataclasses import dataclass, field
from typing import Annotated

import pytest

from warned_dataclasses import (
    warned,
    Warned,
    warn_for_condition,
    ConditionalParameterError,
    ConditionSet,
    warn_all,
    satisfy,
)
from warned_dataclasses.common import ConditionalParameterWarning


@warned(error=False, satisfy_on_warn=False)
@dataclass
class WarningNoSatisfy:
    foo: int = field(default=4)
    bar: Warned[int, "bar"] = field(default=5)
    baz: Warned[int, "baz"] = field(default_factory=lambda: 10)


@warned(error=False, satisfy_on_warn=True)
@dataclass
class WarningSatisfy:
    foo: int = field(default=4)
    bar: Warned[int, "bar"] = field(default=5)
    baz: Warned[int, "baz"] = field(default_factory=lambda: 10)


@warned(error=True, satisfy_on_warn=False)
@dataclass
class ErrorNoSatisfy:
    foo: int = field(default=4)
    bar: Warned[int, "bar"] = field(default=5)
    baz: Warned[int, "baz"] = field(default_factory=lambda: 10)


@warned(error=True)
@dataclass
class ErrorSatisfy:
    foo: int = field(default=4)
    bar: Warned[int, "bar"] = field(default=5)
    baz: Warned[int, "baz"] = field(default_factory=lambda: 10)


@warned(error=True)
@dataclass
class ErrorSatisfy2:
    foo: Warned[str, "foo"] = field(default="abcd1234")
    bar: Warned[str, "bar"] = field(default="sam I am")


def test_no_parens():
    @warned
    @dataclass
    class NoParens:
        f: Warned[int, "f"] = field(default=0)

    np = NoParens(f=1)

    with pytest.warns(ConditionalParameterWarning) as w:
        warn_for_condition(np, "f")
    assert len(w) == 1


def test_satisfy_on_warn_error():
    es = ErrorSatisfy(bar=3)

    with pytest.raises(ConditionalParameterError):
        warn_for_condition(es, "bar")

    warn_for_condition(es, "bar")


def test_satisfy_on_warn_warning():
    ws = WarningSatisfy(bar=3)

    with pytest.warns(ConditionalParameterWarning):
        warn_for_condition(ws, "bar")

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        warn_for_condition(ws, "bar")


def test_satisfy_on_warn_warn_all_error():
    es = ErrorSatisfy(bar=3)

    with pytest.raises(ConditionalParameterError):
        warn_for_condition(es, "bar")

    warn_all(es)


def test_satisfy_on_warn_warn_all_warning():
    es = ErrorSatisfy(bar=3)

    with pytest.raises(ConditionalParameterError):
        warn_for_condition(es, "bar")

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        warn_all(es)


def test_no_satisfy_on_warn_error():
    ens = ErrorNoSatisfy(bar=3)

    with pytest.raises(ConditionalParameterError):
        warn_for_condition(ens, "bar")

    with pytest.raises(ConditionalParameterError):
        warn_for_condition(ens, "bar")


def test_no_satisfy_on_warn_warning():
    wns = WarningNoSatisfy(bar=3)

    with pytest.warns(ConditionalParameterWarning):
        warn_for_condition(wns, "bar")

    with pytest.warns(ConditionalParameterWarning):
        warn_for_condition(wns, "bar")


def test_condition_set_ignore_not_present_in_some():
    es = ErrorSatisfy()
    es2 = ErrorSatisfy2(foo="abc")
    conditions = ConditionSet(es, es2)

    conditions.satisfy("foo")

    conditions.warn_all()


def test_condition_set_error_on_not_present_in_any():
    es = ErrorSatisfy()
    es2 = ErrorSatisfy2(foo="abc")
    conditions = ConditionSet(es, es2)

    with pytest.raises(ValueError):
        conditions.satisfy("nonexistent")

    with pytest.raises(ValueError):
        conditions.warn_for_condition("nonexistent2")


def test_condition_set_error_on_not_present_in_any_functional():
    es = ErrorSatisfy()
    es2 = ErrorSatisfy2(foo="abc")
    conditions = ConditionSet(es, es2)

    with pytest.raises(ValueError) as exc_info:
        satisfy(conditions, "nonexistent")

    with pytest.raises(ValueError) as exc_info:
        warn_for_condition(conditions, "nonexistent2")


def test_condition_set_satisfy():
    es = ErrorSatisfy(bar=3)
    es2 = ErrorSatisfy2(foo="abc", bar="Stephen")
    conditions = ConditionSet(es, es2)

    conditions.satisfy("bar")
    conditions.satisfy("foo")

    conditions.warn_all()


def test_condition_set_satisfy_functional():
    es = ErrorSatisfy(bar=3)
    es2 = ErrorSatisfy2(foo="abc", bar="Stephen")
    conditions = ConditionSet(es, es2)

    satisfy(conditions, "bar")
    satisfy(conditions, "foo")

    warn_all(conditions)


def test_condition_set_warn_for_condition():
    es = ErrorSatisfy(bar=3)
    es2 = ErrorSatisfy2(bar="Stephen")
    conditions = ConditionSet(es, es2)
    with pytest.raises(ConditionalParameterError) as exc_info:
        conditions.warn_for_condition("bar")
    assert len(exc_info.value.args[0].strip().split("\n")) == 3


def test_condition_set_warn_for_condition_functional():
    es = ErrorSatisfy(bar=3)
    es2 = ErrorSatisfy2(bar="Stephen")
    conditions = ConditionSet(es, es2)
    with pytest.raises(ConditionalParameterError) as exc_info:
        warn_for_condition(conditions, "bar")
    assert len(exc_info.value.args[0].strip().split("\n")) == 3


def test_condition_set_warn_all():
    es = ErrorSatisfy(bar=3)
    es2 = ErrorSatisfy2(foo="abc1", bar="Stephen")
    conditions = ConditionSet(es, es2)
    with pytest.raises(ConditionalParameterError) as exc_info:
        conditions.warn_all()
    assert len(exc_info.value.args[0].strip().split("\n")) == 4


def test_condition_set_warn_all_functional():
    es = ErrorSatisfy(bar=3)
    es2 = ErrorSatisfy2(foo="abc1", bar="Stephen")
    conditions = ConditionSet(es, es2)
    with pytest.raises(ConditionalParameterError) as exc_info:
        warn_all(conditions)
    assert len(exc_info.value.args[0].strip().split("\n")) == 4


def test_ignores_other_annotations():
    @warned(error=True)
    @dataclass
    class Qux:
        one: Warned[int, "bar"] = field(default=5)
        two: Annotated[int, {"metadata": "something irrelevant"}] = field(default=0)

    baz = Qux(3, 3)

    with pytest.raises(ConditionalParameterError) as exc_info:
        warn_for_condition(baz, "bar")

    assert len(exc_info.value.args[0].strip().split("\n")) == 2


def test_no_bleed():
    _ = ErrorNoSatisfy(bar=4)
    es = ErrorSatisfy(bar=4)
    conditions = ConditionSet(es)
    with pytest.raises(ConditionalParameterError) as exc_info:
        conditions.warn_for_condition("bar")
    assert len(exc_info.value.args[0].strip().split("\n")) == 2


@pytest.fixture(params=["bar", "baz"])
def condition_var(request):
    return request.param


@pytest.fixture(params=[("bar", "bar", 5), ("baz", "baz", 10)])
def condition_attr_default(request):
    return request.param


def test_ok_on_default_positional(condition_var):
    ens = ErrorNoSatisfy(3)
    warn_for_condition(ens, condition_var)


def test_ok_on_default_kwarg(condition_var):
    ens = ErrorNoSatisfy(foo=3)
    warn_for_condition(ens, condition_var)


def test_ok_on_satisfy_implicit(condition_var):
    ens = ErrorNoSatisfy()
    satisfy(ens, condition_var)
    warn_for_condition(ens, condition_var)


def test_ok_on_satisfy(condition_attr_default):
    condition, attr_name, _ = condition_attr_default
    ens = ErrorNoSatisfy(3, **{attr_name: 6})
    satisfy(ens, condition)
    warn_for_condition(ens, condition)


def test_ok_on_warn_all_implicit():
    ens = ErrorNoSatisfy(3)
    warn_all(ens)


def test_fails_on_warn_all():
    ens = ErrorNoSatisfy(3, bar=4)
    with pytest.raises(ConditionalParameterError):
        warn_all(ens)


def test_warn_all_collects_all_error():
    ens = ErrorNoSatisfy(3, bar=4, baz=9)
    with pytest.raises(ConditionalParameterError) as exc_info:
        warn_all(ens)
    assert len(exc_info.value.args[0].strip().split("\n")) == 3


def test_warn_all_collects_all_warning():
    wns = WarningNoSatisfy(3, bar=4, baz=9)
    with pytest.warns(ConditionalParameterWarning) as w:
        warn_all(wns)
    assert len(w) == 2


def test_warn_all_collects_some():
    ens = ErrorNoSatisfy(3, baz=9)
    with pytest.raises(ConditionalParameterError) as exc_info:
        warn_all(ens)
    assert len(exc_info.value.args[0].strip().split("\n")) == 2


def test_fails_on_positional():
    ens = ErrorNoSatisfy(3, 6)
    with pytest.raises(ConditionalParameterError):
        warn_for_condition(ens, "bar")


def test_fails_on_kwarg(condition_attr_default):
    condition, attr_name, _ = condition_attr_default
    ens = ErrorNoSatisfy(3, **{attr_name: 6})
    with pytest.raises(ConditionalParameterError):
        warn_for_condition(ens, condition)


def test_fails_on_equal_to_default(condition_attr_default):
    condition, attr_name, default = condition_attr_default
    ens = ErrorNoSatisfy(3, **{attr_name: default})
    with pytest.raises(ConditionalParameterError):
        warn_for_condition(ens, condition)
