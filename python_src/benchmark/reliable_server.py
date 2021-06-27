import socket
import argparse
from utils2.logging import logging
from benchmark.config import DEFAULT_UDP_PORT, SEQ_LENGTH, ACK_LENGTH, ACK_BUF, ACK_PREFIX_LENGTH
from benchmark.reliable_utils import is_ack, get_seq, send_ack, timestamp
import numpy as np

logger = logging.getLogger(__name__)
LOG_PATH = '/tmp/webrtc/logs'


def on_packet_ack(pkg_id):
    logger.info(f'Packet acknowledged: {pkg_id}')


def parse_args():
    parser = argparse.ArgumentParser(description='A UDP server that implements reliable transmission')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setblocking(0)
        s.bind(("0.0.0.0", DEFAULT_UDP_PORT))
        while True:
            try:
                data, addr_ = s.recvfrom(1500)
                if is_ack(data):
                    on_packet_ack(get_seq(data))
                else:
                    send_ack(data, s, addr_)
            except BlockingIOError as e:
                pass


if __name__ == '__main__':
    main()
