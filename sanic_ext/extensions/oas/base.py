from abc import ABC
from functools import partial, wraps


class BaseDecorator(ABC):
    def __get__(self, instance, _):
        return wraps(self._func)(partial(self.__call__, instance))

    def __call__(self, func):
        self._func = func
        self.setup()

        def decorator(f):
            @wraps(f)
            def decorated_function(*a, **kw):
                return self.execute(a, kw)

            return decorated_function

        return decorator(func)

    def setup(self):
        ...

    def execute(self, args, kwargs):
        return self._func(*args, **kwargs)
