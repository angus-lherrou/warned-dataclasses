# warned-dataclasses

[![pypi](https://img.shields.io/pypi/v/warned-dataclasses)](https://pypi.org/project/warned-dataclasses) [![codecov](https://img.shields.io/codecov/c/github/lru-dev/warned-dataclasses)](https://app.codecov.io/gh/lru-dev/warned-dataclasses)

This package adds functionality to Python's `dataclasses` feature to 
emit a warning or raise an exception if an explicit value for an 
attribute was used to initialize a dataclass but some user-specified 
condition that that attribute logically relies on was not met.

## Motivation

The primary use case for this package is for tools (such as 🤗 
Transformers) that use `dataclasses` for command-line parsing, where 
different command-line parameters make sense in different scenarios.

In the simple case, a programmer can just emit a warning or raise an 
exception if an explicit value was passed to one of these parameters in 
a context where it is not appropriate. However, the programmer may also 
want to set sensible defaults for such parameters when they are 
appropriate.

One approach to this problem is to compare the runtime value against the 
default value, and assume an explicit value was passed if they do not 
match. However, this approach presents two concerns: 

1. complex and
difficult-to-introspect `default_factory` objects may be used in the
dataclass's fields
2. the programmer may want to warn the user even if they explicitly pass 
the default value

This package presents a solution to both of these problems.

## Installation

This package is on PyPI for Python >=3.8:

```sh
pip install warned-dataclasses
```

## Usage

There are two simple usage paradigms for this package.
The following (contrived) examples should illustrate them.

### 1. `warn_for_condition`

With this approach, warnings are emitted as unmet conditions are 
discovered. This could be useful for emitting relevant warnings amidst
other logging statements describing program flow, or (when using error=True)
if an unmet condition in a critical point in the program should terminate
the program immediately.

```python
import json

from dataclasses import dataclass, field

from warned_dataclasses import Warned, warned, warn_for_condition


@warned
@dataclass
class User:
    id: int
    admin_level: Warned[int, 'admin_only'] = field(default=1)


def check_admin(user: User):
    with open('admins.json', 'r') as admins_fd:
        admins = json.load(admins_fd)

    if user.id not in admins:
        # uh-oh, user is not an admin
        warn_for_condition(user, 'admin_only')


if __name__ == '__main__':
    user = User(123, admin_level=2)
    check_admin(user)
```

### 2. `satisfy` and `warn_all`

With this approach, warnings are suppressed as conditions are judged to
be met and marked as satisfied, and all warnings for a dataclass are
emitted at once when `warn_all` is called.

```python
import json

from dataclasses import dataclass, field

from warned_dataclasses import Warned, warned, warn_all, satisfy


@warned
@dataclass
class User:
    id: int
    admin_level: Warned[int, 'admin_only'] = field(default=1)
    fileshare_home_dir: Warned[str, 'db_access'] = field(default='~')


def check_admin(user: User):
    with open('admins.json', 'r') as admins_fd:
        admins = json.load(admins_fd)

    if user.id in admins:
        # user is an admin; no warning
        satisfy(user, 'admin_only')


def check_db_access(user: User):
    with open('db_users.json', 'r') as db_users_fd:
        db_users = json.load(db_users_fd)

    if user.id in db_users:
        # user is a db user; no warning
        satisfy(user, 'db_access')


if __name__ == '__main__':
    user = User(123, admin_level=2, fileshare_home_dir='/')
    check_admin(user)
    check_db_access(user)

    # now emit all unsatisfied errors
    warn_all(user)
```

## Advanced Usage

### 1. Decorator options

* By default, a warned dataclass will emit a warning to the current `logging` 
  logger. To raise an exception instead, use `@warned(error=True)`.

* By default, a warned dataclass will only emit a warning once for each
  condition; future calls to `warn_for_condition` or `warn_all` will
  treat that condition as satisfied. To disable this behavior and emit
  a warning every time it is invoked, use `@warned(satisfy_on_warn=False)`

* A plain `@warned` can be used with or without parentheses.


### 2. Multiple warned dataclasses and `ConditionSet`

If your code uses multiple warned dataclasses that share some conditions,
the methods illustrated above become clunky, as you end up having to call
`warn_for_condition(obj, condition)` for every warned dataclass object
that uses `condition`. Instead, you can collect conditions immediately
after instantiation using `ConditionSet`, then call any of the usual functions,
either with the `ConditionSet` object as the first parameter or as a
method on `ConditionSet`:

```python
from dataclasses import dataclass, field

from warned_dataclasses import warned, Warned, ConditionSet, warn_for_condition, warn_all, satisfy


@warned
@dataclass
class One:
    ...
    some_attr: Warned[int, 'abc'] = field(default=32)
    other_attr: Warned[str, 'shared_condition'] = field(default='')
    ...


@warned
@dataclass
class Two:
    ...
    some_attr: Warned[int, 'shared_condition'] = field(default=5)
    other_attr: Warned[float, '123'] = field(default=0.0)
    ...


def main():
    ...
    one = One(...)
    two = Two(...)
    
    conditions = ConditionSet(one, two)
    
    ...
    
    conditions.warn_for_condition("shared_condition")
    conditions.satisfy("123")
    conditions.warn_all()
    
    # or:
    
    warn_for_condition(conditions, "shared_condition")
    satisfy(conditions, "123")
    warn_all(conditions)

```
