import socket
from pathlib import Path
import argparse
import os
import json
import numpy as np
from benchmark.reliable_utils import is_ack, get_seq, send_ack, timestamp
from benchmark.config import DEFAULT_UDP_PORT, SEQ_LENGTH, BYTE_ORDER
from utils2.logging import logging
from benchmark.cc.cc import CongestionControl
from benchmark.cc.bbr import BBR
from benchmark.cc.static import StaticPacing

logger = logging.getLogger(__name__)
LOG_PATH = '/tmp/webrtc/logs'
LOG_PERIOD = 5
STATICS_SIZE = 1024 * 1024


class Context(object):
    def __init__(self, duration, interval, pkg_size):
        self.duration: int = duration
        self.interval: int = interval
        self.pkg_size: int = pkg_size
        self.packet_send_statics = np.zeros((STATICS_SIZE,), dtype=float)
        self.packet_recv_statics = np.zeros((STATICS_SIZE,), dtype=float)
        self.send_seq = 0
        self.start_ts = 0


def on_packet_ack(pkg_id, cc: CongestionControl, ctx: Context):
    # logger.info(f'Packet acknowledged: {pkg_id}')
    ctx.packet_recv_statics[pkg_id] = timestamp()
    cc.on_ack(pkg_id)


def maybe_send(s: socket.socket, cc: CongestionControl, ctx: Context):
    if cc.next(ctx.send_seq):
        buf = bytearray(SEQ_LENGTH + 10)
        buf[:SEQ_LENGTH] = ctx.send_seq.to_bytes(SEQ_LENGTH, byteorder=BYTE_ORDER)
        try:
            s.send(buf)
            ctx.packet_send_statics[ctx.send_seq] = timestamp()
            cc.on_sent(ctx.send_seq, True)
            ctx.send_seq += 1
        except BlockingIOError:
            cc.on_sent(ctx.send_seq, False)


def parse_args():
    parser = argparse.ArgumentParser(description='A UDP client that implements reliable transmission')
    parser.add_argument('-s', '--size', type=int, default=1460, help='UDP packet size')
    parser.add_argument('-t', '--time', type=int, default=15, help='Duration of the test, in seconds')
    parser.add_argument('-i', '--interval', type=int, default=10,
                        help='The interval of sending packets, in milliseconds')
    parser.add_argument('-c', '--congestion-control', type=str, choices=['bbr', 'static'], default='static',
                        help='The congestion control algorithm')
    args = parser.parse_args()
    return args


def get_congestion_control(cc, ctx: Context) -> CongestionControl:
    if cc == 'static':
        return StaticPacing(ctx.interval)
    if cc == 'bbr':
        return BBR()


def main():
    Path(LOG_PATH).mkdir(parents=True, exist_ok=True)
    args = parse_args()
    ctx = Context(args.time, args.interval, args.size)
    last_log = 0
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setblocking(0)
        s.connect(("127.0.0.1", DEFAULT_UDP_PORT))
        cc = get_congestion_control(args.congestion_control, ctx)
        ctx.start_ts = timestamp()
        while timestamp() - ctx.start_ts < ctx.duration:
            if (timestamp() - last_log) > LOG_PERIOD:
                logger.info(f'{int(timestamp() - ctx.start_ts)}s has passed')
                last_log = timestamp()
            try:
                data, addr_ = s.recvfrom(2500)
                if is_ack(data):
                    on_packet_ack(get_seq(data), cc, ctx)
                else:
                    send_ack(data, s, addr_)
            except (BlockingIOError, ConnectionRefusedError) as e:
                pass
            try:
                maybe_send(s, cc, ctx)
            except BlockingIOError as e:
                pass
    statics = {'seq': ctx.send_seq, 'sent_ts': ctx.packet_send_statics[:ctx.send_seq].tolist(),
               'received_ts': ctx.packet_recv_statics[:ctx.send_seq].tolist()}
    logger.info('Finished experiment, dumping logs')
    json.dump(statics, open(os.path.join(LOG_PATH, "reliable.json"), 'w+'))


if __name__ == '__main__':
    main()
