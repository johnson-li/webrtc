from benchmark.config import ACK_LENGTH, ACK_BUF, SEQ_LENGTH, ACK_PREFIX_LENGTH, BYTE_ORDER, TIMESTAMP_BYTES
from datetime import datetime
import time


def try_to_parse_ack(data):
    if len(data) == ACK_LENGTH and data[:3] == ACK_BUF:
        seq = int.from_bytes(data[ACK_PREFIX_LENGTH: ACK_PREFIX_LENGTH + SEQ_LENGTH], byteorder=BYTE_ORDER)
        recv_ts = int.from_bytes(data[ACK_PREFIX_LENGTH + SEQ_LENGTH:], byteorder=BYTE_ORDER) / 1000
        return True, seq, recv_ts
    return False, None, None


def send_ack(data, s, addr):
    buf_ack = bytearray(ACK_LENGTH)
    buf_ack[:ACK_PREFIX_LENGTH] = ACK_BUF
    buf_ack[ACK_PREFIX_LENGTH: ACK_PREFIX_LENGTH + SEQ_LENGTH] = data[:SEQ_LENGTH]
    buf_ack[ACK_PREFIX_LENGTH + SEQ_LENGTH:] = int(1000 * timestamp()).to_bytes(TIMESTAMP_BYTES, byteorder=BYTE_ORDER)
    s.sendto(buf_ack, addr)


def timestamp():
    return time.monotonic()


def log_id():
    return int(datetime.today().timestamp())
