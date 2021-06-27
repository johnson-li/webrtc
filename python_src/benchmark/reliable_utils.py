from benchmark.config import ACK_LENGTH, ACK_BUF, SEQ_LENGTH, ACK_PREFIX_LENGTH, BYTE_ORDER
import time


def is_ack(data):
    return len(data) == ACK_LENGTH and data[:3] == ACK_BUF


def get_seq(data):
    return int.from_bytes(data[3:], byteorder=BYTE_ORDER)


def send_ack(data, s, addr):
    buf_ack = bytearray(ACK_LENGTH)
    buf_ack[:ACK_PREFIX_LENGTH] = ACK_BUF
    buf_ack[3:] = data[:SEQ_LENGTH]
    s.sendto(buf_ack, addr)


def timestamp():
    return time.monotonic()
