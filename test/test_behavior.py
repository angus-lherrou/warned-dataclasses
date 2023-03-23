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
    satisfy
)


@warned(error=True)
@dataclass
class Foo:
    bar: int = field(default=4)
    baz: Warned[int, "dflt"] = field(default=5)
    qux: Warned[int, "dflt_fac"] = field(default_factory=lambda: 10)


@warned(error=True)
@dataclass
class Bar:
    bar: int = field(default=4)
    baz: Warned[int, "dflt"] = field(default=5)
    qux: Warned[int, "dflt_fac"] = field(default_factory=lambda: 10)


@warned(error=True)
@dataclass
class Baz:
    name: Warned[str, "dflt"] = field(default="sam I am")
    ident: Warned[str, "ident"] = field(default="abcd1234")


def test_condition_set_ignore_not_present_in_some():
    bar = Bar()
    baz = Baz(ident="abc")
    conditions = ConditionSet(bar, baz)

    conditions.satisfy("ident")

    conditions.warn_all()


def test_condition_set_error_on_not_present_in_any():
    bar = Bar()
    baz = Baz(ident="abc")
    conditions = ConditionSet(bar, baz)

    with pytest.raises(ValueError) as exc_info:
        conditions.satisfy("nonexistent")

    with pytest.raises(ValueError) as exc_info:
        conditions.warn_for_condition("nonexistent2")


def test_condition_set_error_on_not_present_in_any_functional():
    bar = Bar()
    baz = Baz(ident="abc")
    conditions = ConditionSet(bar, baz)

    with pytest.raises(ValueError) as exc_info:
        satisfy(conditions, "nonexistent")

    with pytest.raises(ValueError) as exc_info:
        warn_for_condition(conditions, "nonexistent2")


def test_condition_set_satisfy():
    bar = Bar(baz=3)
    baz = Baz(name="Stephen", ident="abc")
    conditions = ConditionSet(bar, baz)

    conditions.satisfy("dflt")
    conditions.satisfy("ident")

    conditions.warn_all()


def test_condition_set_satisfy_functional():
    bar = Bar(baz=3)
    baz = Baz(name="Stephen", ident="abc")
    conditions = ConditionSet(bar, baz)

    satisfy(conditions, "dflt")
    satisfy(conditions, "ident")

    warn_all(conditions)


def test_condition_set_warn_for_condition():
    bar = Bar(baz=3)
    baz = Baz(name="Stephen")
    conditions = ConditionSet(bar, baz)
    with pytest.raises(ConditionalParameterError) as exc_info:
        conditions.warn_for_condition("dflt")
    assert len(exc_info.value.args[0].strip().split("\n")) == 3


def test_condition_set_warn_for_condition_functional():
    bar = Bar(baz=3)
    baz = Baz(name="Stephen")
    conditions = ConditionSet(bar, baz)
    with pytest.raises(ConditionalParameterError) as exc_info:
        warn_for_condition(conditions, "dflt")
    with pytest.raises(ConditionalParameterError) as exc_info_2:
        conditions.warn_for_condition("dflt")
    assert len(exc_info.value.args[0].strip().split("\n")) == 3
    assert exc_info.value.args[0] == exc_info_2.value.args[0]


def test_condition_set_warn_all():
    bar = Bar(baz=3)
    baz = Baz(name="Stephen", ident="abc1")
    conditions = ConditionSet(bar, baz)
    with pytest.raises(ConditionalParameterError) as exc_info:
        conditions.warn_all()
    assert len(exc_info.value.args[0].strip().split("\n")) == 4


def test_condition_set_warn_all_functional():
    bar = Bar(baz=3)
    baz = Baz(name="Stephen", ident="abc1")
    conditions = ConditionSet(bar, baz)
    with pytest.raises(ConditionalParameterError) as exc_info:
        warn_all(conditions)
    with pytest.raises(ConditionalParameterError) as exc_info_2:
        conditions.warn_all()
    assert len(exc_info.value.args[0].strip().split("\n")) == 4
    assert exc_info.value.args[0] == exc_info_2.value.args[0]


def test_ignores_other_annotations():
    @warned(error=True)
    @dataclass
    class Qux:
        one: Warned[int, "dflt"] = field(default=5)
        two: Annotated[int, {"metadata": "something irrelevant"}] = field(default=0)

    qux = Qux(3, 3)

    with pytest.raises(ConditionalParameterError) as exc_info:
        warn_for_condition(qux, "dflt")

    assert len(exc_info.value.args[0].strip().split("\n")) == 2


def test_no_bleed():
    _ = Foo(baz=4)
    bar = Bar(baz=4)
    conditions = ConditionSet(bar)
    with pytest.raises(ConditionalParameterError) as exc_info:
        conditions.warn_for_condition("dflt")
    assert len(exc_info.value.args[0].strip().split("\n")) == 2


@pytest.fixture(params=["dflt", "dflt_fac"])
def condition_var(request):
    return request.param


@pytest.fixture(params=[("dflt", "baz", 5), ("dflt_fac", "qux", 10)])
def condition_attr_default(request):
    return request.param


def test_ok_on_default_positional(condition_var):
    foo = Foo(3)
    warn_for_condition(foo, condition_var)


def test_ok_on_default_kwarg(condition_var):
    foo = Foo(bar=3)
    warn_for_condition(foo, condition_var)


def test_ok_on_satisfy_implicit(condition_var):
    foo = Foo()
    satisfy(foo, condition_var)
    warn_for_condition(foo, condition_var)


def test_ok_on_satisfy(condition_attr_default):
    condition, attr_name, _ = condition_attr_default
    foo = Foo(3, **{attr_name: 6})
    satisfy(foo, condition)
    warn_for_condition(foo, condition)


def test_ok_on_warn_all_implicit():
    foo = Foo(3)
    warn_all(foo)


def test_fails_on_warn_all():
    foo = Foo(3, baz=4)
    with pytest.raises(ConditionalParameterError):
        warn_all(foo)


def test_warn_all_collects_all():
    foo = Foo(3, baz=4, qux=9)
    with pytest.raises(ConditionalParameterError) as exc_info:
        warn_all(foo)
    assert len(exc_info.value.args[0].strip().split("\n")) == 3


def test_warn_all_collects_some():
    foo = Foo(3, qux=9)
    with pytest.raises(ConditionalParameterError) as exc_info:
        warn_all(foo)
    assert len(exc_info.value.args[0].strip().split("\n")) == 2


def test_fails_on_positional():
    foo = Foo(3, 6)
    with pytest.raises(ConditionalParameterError):
        warn_for_condition(foo, "dflt")


def test_fails_on_kwarg(condition_attr_default):
    condition, attr_name, _ = condition_attr_default
    foo = Foo(3, **{attr_name: 6})
    with pytest.raises(ConditionalParameterError):
        warn_for_condition(foo, condition)


def test_fails_on_equal_to_default(condition_attr_default):
    condition, attr_name, default = condition_attr_default
    foo = Foo(3, **{attr_name: default})
    with pytest.raises(ConditionalParameterError):
        warn_for_condition(foo, condition)
