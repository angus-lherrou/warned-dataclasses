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
    invoke,
    satisfy,
    ConditionalParameterError,
)


@warned(error_on_invoke=True)
@dataclass
class Foo:
    bar: int = field(default=4)
    baz: Warned[int, "dflt"] = field(default=5)
    qux: Warned[int, "dflt_fac"] = field(default_factory=lambda: 10)


@pytest.fixture(params=["dflt", "dflt_fac"])
def condition(request):
    return request.param


@pytest.fixture(params=[("dflt", "baz", 5), ("dflt_fac", "qux", 10)])
def condition_attr_default(request):
    return request.param


def test_ok_on_default_positional(condition):
    foo = Foo(3)
    invoke(foo, condition)


def test_ok_on_default_kwarg(condition):
    foo = Foo(bar=3)
    invoke(foo, condition)


def test_ok_on_satisfy_implicit(condition):
    foo = Foo()
    satisfy(foo, condition)
    invoke(foo, condition)


def test_ok_on_satisfy(condition_attr_default):
    condition, attr_name, _ = condition_attr_default
    foo = Foo(3, **{attr_name: 6})
    satisfy(foo, condition)
    invoke(foo, condition)


def test_fails_on_positional():
    foo = Foo(3, 6)
    with pytest.raises(ConditionalParameterError):
        invoke(foo, "dflt")


def test_fails_on_kwarg(condition_attr_default):
    condition, attr_name, _ = condition_attr_default
    foo = Foo(3, **{attr_name: 6})
    with pytest.raises(ConditionalParameterError):
        invoke(foo, condition)


def test_fails_on_equal_to_default(condition_attr_default):
    condition, attr_name, default = condition_attr_default
    foo = Foo(3, **{attr_name: default})
    with pytest.raises(ConditionalParameterError):
        invoke(foo, condition)
