import logging
import inspect
import sys
import time
from functools import wraps


logging.basicConfig(level=logging.INFO)
logging.getLogger('paramiko.transport').setLevel(logging.WARNING)


class Logger():
    def __init__(self, file, level, msg):
        self._logger = logging.getLogger(file)
        self._level = level
        self._msg = msg

    def __enter__(self):
        self._ts = time.time()
        self._logger.log(self._level,
                '╔═══════════ %s ═══════════════' % (self._msg))
        return self

    def __exit__(self, type, value, traceback):
        self._logger.log(self._level, '╚═══════════ Costs: %f s══════════════════════' % (time.time() - self._ts))

    def log(self, msg, level=None):
        if not level:
            level = self._level
        self._logger.log(level, '║  %s' % msg)


def get_logger(msg, file=None, level=logging.INFO):
    if not file:
        file = inspect.getfile(sys._getframe(1))
    return Logger(file, level, msg)


def logging_wrapper(msg=None, level=logging.INFO):
    file = inspect.getfile(sys._getframe(1))
    def wrapper(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            with get_logger(msg if msg else 'Function: %s' % func.__name__, file=file, level=level) as logger:
                ans = func(*args, **kwargs, logger=logger)
            return ans
        return wrapped
    return wrapper


@logging_wrapper(msg='demo')
def demo():
    pass


def test():
    demo()


if __name__ == '__main__':
    test()

