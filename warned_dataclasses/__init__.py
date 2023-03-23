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

from typing_extensions import Annotated as Warned
from .main import warned, warn_for_condition, warn_all, ConditionSet, satisfy
from .common import ConditionalParameterError

__all__ = [
    "ConditionSet",
    "ConditionalParameterError",
    "Warned",
    "warn_all",
    "warn_for_condition",
    "warned",
    "satisfy",
]
