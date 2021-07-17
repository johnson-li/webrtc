import logging
from datetime import datetime


logging.basicConfig(level=logging.INFO)


def log_id():
    return int(datetime.today().timestamp())
