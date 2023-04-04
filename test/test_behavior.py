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

import warnings
from dataclasses import dataclass, field
from typing_extensions import Annotated

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
    not_warned: int = field(default=4)
    dflt: Warned[int, "dflt"] = field(default=5)
    dflt_fac: Warned[int, "dflt_fac"] = field(default_factory=lambda: 10)


@warned(error=False, satisfy_on_warn=True)
@dataclass
class WarningSatisfy:
    not_warned: int = field(default=4)
    dflt: Warned[int, "dflt"] = field(default=5)
    dflt_fac: Warned[int, "dflt_fac"] = field(default_factory=lambda: 10)


@warned(error=True, satisfy_on_warn=False)
@dataclass
class ErrorNoSatisfy:
    not_warned: int = field(default=4)
    dflt: Warned[int, "dflt"] = field(default=5)
    dflt_fac: Warned[int, "dflt_fac"] = field(default_factory=lambda: 10)


@warned(error=True)
@dataclass
class ErrorSatisfy:
    not_warned: int = field(default=4)
    dflt: Warned[int, "dflt"] = field(default=5)
    dflt_fac: Warned[int, "dflt_fac"] = field(default_factory=lambda: 10)


@warned(error=True, warn_on_default=False)
@dataclass
class OddsAndEnds:
    non_default: Warned[int, "non_default"]
    non_init: Annotated[int, "non_init"] = field(default=3, init=False)


@warned(error=True)
@dataclass
class ErrorSatisfy2:
    not_warned: Warned[str, "not_warned"] = field(default="abcd1234")
    dflt: Warned[str, "dflt"] = field(default="sam I am")


@warned(error=True, warn_on_default=False)
@dataclass
class ErrorNoWarnOnDefault:
    not_warned: int = field(default=4)
    dflt: Warned[int, "dflt"] = field(default=5)
    dflt_fac: Warned[int, "dflt_fac"] = field(default_factory=lambda: 10)


@dataclass
class UnwarnedSuperclass:
    not_warned: int = field(default=4)


@warned(error=False)
@dataclass
class WarnedWarningMidclass(UnwarnedSuperclass):
    dflt: Warned[int, "dflt"] = field(default=5)


@warned(error=False)
@dataclass
class WarnedWarningSubclass(WarnedWarningMidclass):
    dflt_fac: Warned[int, "dflt_fac"] = field(default_factory=lambda: 10)


@warned(error=True)
@dataclass
class WarnedConvErrorSubclass(WarnedWarningMidclass):
    dflt_fac: Warned[int, "dflt_fac"] = field(default_factory=lambda: 10)


@warned(error=True)
@dataclass
class WarnedErrorMidclass(UnwarnedSuperclass):
    dflt: Warned[int, "dflt"] = field(default=5)


@warned(error=True)
@dataclass
class WarnedErrorSubclass(WarnedErrorMidclass):
    dflt_fac: Warned[int, "dflt_fac"] = field(default_factory=lambda: 10)


@warned(error=False)
@dataclass
class WarnedConvWarningSubclass(WarnedErrorMidclass):
    dflt_fac: Warned[int, "dflt_fac"] = field(default_factory=lambda: 10)


def test_midclass_error():
    wem = WarnedErrorMidclass(dflt=6)
    with pytest.raises(ConditionalParameterError):
        warn_for_condition(wem, "dflt")


def test_midclass_warning():
    wwm = WarnedWarningMidclass(dflt=6)
    with pytest.warns(ConditionalParameterWarning):
        warn_for_condition(wwm, "dflt")


def test_subclass_converted_error():
    wces = WarnedConvErrorSubclass(dflt=6, dflt_fac=11)
    with pytest.raises(ConditionalParameterError):
        warn_for_condition(wces, "dflt_fac")


@pytest.mark.xfail
def test_subclass_convert_prev_to_error():
    wces = WarnedConvErrorSubclass(dflt=6)
    with pytest.raises(ConditionalParameterError):
        warn_for_condition(wces, "dflt")


def test_subclass_converted_warning():
    wcws = WarnedConvWarningSubclass(dflt=6, dflt_fac=11)
    with pytest.warns(ConditionalParameterWarning):
        warn_for_condition(wcws, "dflt_fac")


@pytest.mark.xfail
def test_subclass_convert_prev_to_warning():
    wcws = WarnedConvWarningSubclass(dflt=6)
    with pytest.warns(ConditionalParameterWarning):
        warn_for_condition(wcws, "dflt")


def test_subclass_error_both_work():
    wes = WarnedErrorSubclass(dflt=6, dflt_fac=11)
    with pytest.raises(ConditionalParameterError):
        warn_for_condition(wes, "dflt")
    with pytest.raises(ConditionalParameterError):
        warn_for_condition(wes, "dflt_fac")


def test_subclass_warning_both_work():
    wws = WarnedWarningSubclass(dflt=6, dflt_fac=11)
    with pytest.warns(ConditionalParameterWarning):
        warn_for_condition(wws, "dflt")
    with pytest.warns(ConditionalParameterWarning):
        warn_for_condition(wws, "dflt_fac")


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
    es = ErrorSatisfy(dflt=3)

    with pytest.raises(ConditionalParameterError):
        warn_for_condition(es, "dflt")

    warn_for_condition(es, "dflt")


def test_satisfy_on_warn_warning():
    ws = WarningSatisfy(dflt=3)

    with pytest.warns(ConditionalParameterWarning):
        warn_for_condition(ws, "dflt")

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        warn_for_condition(ws, "dflt")


def test_satisfy_on_warn_warn_all_error():
    es = ErrorSatisfy(dflt=3)

    with pytest.raises(ConditionalParameterError):
        warn_for_condition(es, "dflt")

    warn_all(es)


def test_satisfy_on_warn_warn_all_warning():
    es = ErrorSatisfy(dflt=3)

    with pytest.raises(ConditionalParameterError):
        warn_for_condition(es, "dflt")

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        warn_all(es)


def test_no_satisfy_on_warn_error():
    ens = ErrorNoSatisfy(dflt=3)

    with pytest.raises(ConditionalParameterError):
        warn_for_condition(ens, "dflt")

    with pytest.raises(ConditionalParameterError):
        warn_for_condition(ens, "dflt")


def test_no_satisfy_on_warn_warning():
    wns = WarningNoSatisfy(dflt=3)

    with pytest.warns(ConditionalParameterWarning):
        warn_for_condition(wns, "dflt")

    with pytest.warns(ConditionalParameterWarning):
        warn_for_condition(wns, "dflt")


def test_condition_set_ignore_not_present_in_some():
    es = ErrorSatisfy()
    es2 = ErrorSatisfy2(not_warned="abc")
    conditions = ConditionSet(es, es2)

    conditions.satisfy("not_warned")

    conditions.warn_all()


def test_condition_set_error_on_not_present_in_any():
    es = ErrorSatisfy()
    es2 = ErrorSatisfy2(not_warned="abc")
    conditions = ConditionSet(es, es2)

    with pytest.raises(ValueError):
        conditions.satisfy("nonexistent")

    with pytest.raises(ValueError):
        conditions.warn_for_condition("nonexistent2")


def test_condition_set_error_on_not_present_in_any_functional():
    es = ErrorSatisfy()
    es2 = ErrorSatisfy2(not_warned="abc")
    conditions = ConditionSet(es, es2)

    with pytest.raises(ValueError):
        satisfy(conditions, "nonexistent")

    with pytest.raises(ValueError):
        warn_for_condition(conditions, "nonexistent2")


def test_condition_set_satisfy():
    es = ErrorSatisfy(dflt=3)
    es2 = ErrorSatisfy2(not_warned="abc", dflt="Stephen")
    conditions = ConditionSet(es, es2)

    conditions.satisfy("dflt")
    conditions.satisfy("not_warned")

    conditions.warn_all()


def test_condition_set_satisfy_functional():
    es = ErrorSatisfy(dflt=3)
    es2 = ErrorSatisfy2(not_warned="abc", dflt="Stephen")
    conditions = ConditionSet(es, es2)

    satisfy(conditions, "dflt")
    satisfy(conditions, "not_warned")

    warn_all(conditions)


def test_condition_set_warn_for_condition():
    es = ErrorSatisfy(dflt=3)
    es2 = ErrorSatisfy2(dflt="Stephen")
    conditions = ConditionSet(es, es2)
    with pytest.raises(ConditionalParameterError) as exc_info:
        conditions.warn_for_condition("dflt")
    assert len(exc_info.value.args[0].strip().split("\n")) == 3


def test_condition_set_warn_for_condition_functional():
    es = ErrorSatisfy(dflt=3)
    es2 = ErrorSatisfy2(dflt="Stephen")
    conditions = ConditionSet(es, es2)
    with pytest.raises(ConditionalParameterError) as exc_info:
        warn_for_condition(conditions, "dflt")
    assert len(exc_info.value.args[0].strip().split("\n")) == 3


def test_condition_set_warn_all():
    es = ErrorSatisfy(dflt=3)
    es2 = ErrorSatisfy2(not_warned="abc1", dflt="Stephen")
    conditions = ConditionSet(es, es2)
    with pytest.raises(ConditionalParameterError) as exc_info:
        conditions.warn_all()
    assert len(exc_info.value.args[0].strip().split("\n")) == 4


def test_condition_set_warn_all_functional():
    es = ErrorSatisfy(dflt=3)
    es2 = ErrorSatisfy2(not_warned="abc1", dflt="Stephen")
    conditions = ConditionSet(es, es2)
    with pytest.raises(ConditionalParameterError) as exc_info:
        warn_all(conditions)
    assert len(exc_info.value.args[0].strip().split("\n")) == 4


def test_ignores_other_annotations():
    @warned(error=True)
    @dataclass
    class Qux:
        one: Warned[int, "dflt"] = field(default=5)
        two: Annotated[int, {"metadata": "something irrelevant"}] = field(default=0)

    dflt_fac = Qux(3, 3)

    with pytest.raises(ConditionalParameterError) as exc_info:
        warn_for_condition(dflt_fac, "dflt")

    assert len(exc_info.value.args[0].strip().split("\n")) == 2


def test_no_bleed():
    _ = ErrorNoSatisfy(dflt=4)
    es = ErrorSatisfy(dflt=4)
    conditions = ConditionSet(es)
    with pytest.raises(ConditionalParameterError) as exc_info:
        conditions.warn_for_condition("dflt")
    assert len(exc_info.value.args[0].strip().split("\n")) == 2


@pytest.fixture(params=["dflt", "dflt_fac"])
def condition_var(request):
    return request.param


@pytest.fixture(params=[("dflt", "dflt", 5), ("dflt_fac", "dflt_fac", 10)])
def condition_attr_default(request):
    return request.param


def test_ok_on_default_positional(condition_var):
    ens = ErrorNoSatisfy(3)
    warn_for_condition(ens, condition_var)


def test_ok_on_default_kwarg(condition_var):
    ens = ErrorNoSatisfy(not_warned=3)
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
    ens = ErrorNoSatisfy(3, dflt=4)
    with pytest.raises(ConditionalParameterError):
        warn_all(ens)


def test_warn_all_collects_all_error():
    ens = ErrorNoSatisfy(3, dflt=4, dflt_fac=9)
    with pytest.raises(ConditionalParameterError) as exc_info:
        warn_all(ens)
    assert len(exc_info.value.args[0].strip().split("\n")) == 3


def test_warn_all_collects_all_warning():
    wns = WarningNoSatisfy(3, dflt=4, dflt_fac=9)
    with pytest.warns(ConditionalParameterWarning) as w:
        warn_all(wns)
    assert len(w) == 2


def test_warn_all_collects_some():
    ens = ErrorNoSatisfy(3, dflt_fac=9)
    with pytest.raises(ConditionalParameterError) as exc_info:
        warn_all(ens)
    assert len(exc_info.value.args[0].strip().split("\n")) == 2


def test_fails_on_positional():
    ens = ErrorNoSatisfy(3, 6)
    with pytest.raises(ConditionalParameterError):
        warn_for_condition(ens, "dflt")


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


def check_recwarn(rw, attr_name):
    assert len(rw) <= 1
    if len(rw) == 1:
        assert attr_name == "dflt_fac"
        w = rw.pop(UserWarning)
        msg = w.message.args[0]
        assert "pure function" in msg
    else:  # len(rw) == 0
        assert attr_name == "dflt"


def test_ok_on_equal_to_default_no_warn_on_default(condition_attr_default, recwarn):
    condition, attr_name, default = condition_attr_default
    enwod = ErrorNoWarnOnDefault(3, **{attr_name: default})
    check_recwarn(recwarn, attr_name)
    warn_for_condition(enwod, condition)


def test_fails_on_non_default_no_warn_on_default(condition_attr_default, recwarn):
    condition, attr_name, default = condition_attr_default
    enwod = ErrorNoWarnOnDefault(3, **{attr_name: default + 1})
    check_recwarn(recwarn, attr_name)
    with pytest.raises(ConditionalParameterError):
        warn_for_condition(enwod, condition)


def test_fails_on_non_init():
    oe = OddsAndEnds(non_default=5)
    with pytest.raises(ConditionalParameterError):
        warn_for_condition(oe, "non_init")


def test_fails_on_non_default():
    oe = OddsAndEnds(non_default=5)
    with pytest.raises(ConditionalParameterError):
        warn_for_condition(oe, "non_default")


def test_error_on_incorrect_condition_name_warn():
    ens = ErrorNoSatisfy()
    with pytest.raises(ValueError) as ve:
        warn_for_condition(ens, "notACondition")
    assert ve.value.args[0][:40] == "Condition notACondition not present for "


def test_error_on_incorrect_condition_name_satisfy():
    ens = ErrorNoSatisfy()
    with pytest.raises(ValueError) as ve:
        satisfy(ens, "notACondition")
    assert ve.value.args[0][:40] == "Condition notACondition not present for "


def test_error_on_warned_non_dataclass():
    with pytest.raises(ValueError) as ve:

        @warned
        class NonDataclass:
            foo: Warned[int, "foo"]

    assert ve.value.args[0] == "@warned should only be used with a dataclass."
