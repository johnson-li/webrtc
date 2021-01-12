import os
import json
from pathlib import Path
from utils.base import RESULT_CACHE_PATH
from functools import wraps
import inspect


def cache(func):
    Path(RESULT_CACHE_PATH).mkdir(parents=True, exist_ok=True)
    file_name = inspect.getfile(func).split('/')[-1][:-3]
    cache_name = f'{file_name}_{func.__name__}'
    export_path = os.path.join(RESULT_CACHE_PATH, f'{cache_name}.json')

    @wraps(func)
    def wrap(*args, **kwargs):
        meta_path = os.path.join(RESULT_CACHE_PATH, f'{cache_name}.meta')
        meta = kwargs.copy()
        meta.update(dict(zip(func.__code__.co_varnames, args)))
        if os.path.isfile(meta_path):
            try:
                meta_old = json.load(open(meta_path))
                if meta == meta_old and os.path.isfile(export_path) and os.path.getsize(export_path) > 0:
                    # pass
                    return json.load(open(export_path))
            except Exception as e:
                pass
        res = func(*args, **kwargs)
        json.dump(meta, open(meta_path, 'w+'))
        json.dump(res, open(export_path, 'w+'))
        print(f"Export log to {export_path}")
        return res

    wrap.__cache_name__ = f'{file_name}_{func.__name__}'
    return wrap


def read_cache(func):
    export_path = os.path.join(RESULT_CACHE_PATH, f'{func.__cache_name__}.json')
    return json.load(open(export_path))
