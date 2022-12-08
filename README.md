# warned-dataclasses

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

## Usage

Using this package is simple. The following (contrived) example should 
illustrate the usage:

```python
import json

from dataclasses import dataclass, field

from warned_dataclasses import Warned, warned, satisfy, invoke


@warned
@dataclass
class User:
    id: int
    admin_level: Warned[int, 'admin_only'] = field(default=1)

    
def check_admin(user: User):
    with open('admins.json', 'r') as admins_fd:
        admins = json.load(admins_fd)
    
    if user.id not in admins:
        # uh-oh, user 123 is not an admin
        invoke(user, 'admin_only')


if __name__ == '__main__':
    user = User(123, admin_level=2)
    check_admin(user)
```

By default, `@warned` will emit a warning to the current `logging` 
logger. To raise an exception instead, use `@warned(error_on_invoke=True)`.

A plain `@warned` can be used with or without parentheses.
