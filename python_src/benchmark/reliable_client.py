import socket
import argparse
import os
import json
import numpy as np
from pathlib import Path
from benchmark.reliable_utils import is_ack, get_seq, send_ack, timestamp
from benchmark.config import DEFAULT_UDP_PORT, SEQ_LENGTH, BYTE_ORDER, IP_HEADER_SIZE, UDP_HEADER_SIZE
from utils2.logging import logging
from benchmark.cc.cc import CongestionControl, SentPacket, NetworkControllerConfig, TransportPacketsFeedback, \
    PacketResult
from benchmark.cc.bbr import BbrNetworkController
from benchmark.cc.static import StaticPacing

logger = logging.getLogger(__name__)
FINE_LOG = False
LOG_PERIOD = 1
LOG_TS = 0
MIN_LOG_PERIOD = 0.01
STATICS_SIZE = 1024 * 1024
BURST_PERIOD = 0.00
kDefaultMinPacketLimit = 0.005
kCongestedPacketInterval = 0.5
kPausedProcessInterval = kCongestedPacketInterval


class Context(object):
    def __init__(self, duration, interval, pkg_size):
        self.duration: int = duration
        self.interval: int = interval
        self.pkg_size: int = pkg_size
        self.packet_send_ts = np.zeros((STATICS_SIZE,), dtype=float)
        self.packet_recv_ts = np.zeros((STATICS_SIZE,), dtype=float)
        self.sent_packet_record = [None] * STATICS_SIZE
        self.send_seq = 0
        self.start_ts = 0
        self.in_flight = set()
        self.last_send_time = 0
        self.last_process_time = 0
        self.pacing_rate = 0
        self.last_ack_sequence_num = 0
        self.congestion_window = float('inf')
        self.rtt = float('inf')
        self.target_rate = 0
        self.burst_period = 0

    def get_pkg_size(self, ip_header=False):
        if ip_header:
            return self.pkg_size + IP_HEADER_SIZE + UDP_HEADER_SIZE
        return self.pkg_size

    def get_outstanding_data(self):
        return len(self.in_flight) * self.get_pkg_size(True)

    def congested(self):
        return self.get_outstanding_data() > self.congestion_window + self.burst_period * self.pacing_rate


def on_packet_ack(pkg_id, cc: CongestionControl, ctx: Context):
    if pkg_id not in ctx.in_flight:
        # logger.info(f'Packet is acked too late: {pkg_id}')
        return
    now = timestamp()
    feedback = TransportPacketsFeedback()
    feedback.feedback_time = now
    lost_pkg_ids = list()
    feedback.prior_in_flight = ctx.get_outstanding_data()
    ctx.in_flight.remove(pkg_id)
    ctx.last_ack_sequence_num = max(pkg_id, ctx.last_ack_sequence_num)
    ctx.packet_recv_ts[pkg_id] = now
    pr = PacketResult()
    pr.sent_packet = ctx.sent_packet_record[pkg_id]
    pr.receive_time = now
    feedback.packet_feedbacks.append(pr)
    if ctx.last_ack_sequence_num and ctx.packet_send_ts[ctx.last_ack_sequence_num]:
        feedback.first_unacked_send_time = ctx.packet_send_ts[ctx.last_ack_sequence_num]
    for i in ctx.in_flight:
        if now > ctx.packet_send_ts[i] + 8 * ctx.rtt:
            lost_pkg_ids.append(i)
    # if lost_pkg_ids:
    #     logger.info(f'lost packets: {lost_pkg_ids}, acked packet: {pkg_id}')
    for i in lost_pkg_ids:
        ctx.in_flight.remove(i)
        pr = PacketResult()
        pr.sent_packet = ctx.sent_packet_record[pkg_id]
        feedback.packet_feedbacks.append(pr)
    feedback.data_in_flight = ctx.get_outstanding_data()
    update = cc.on_transport_packets_feedback(feedback)
    if update:
        if update.pacer_config:
            ctx.pacing_rate = update.pacer_config.data_rate()
        if update.congestion_window:
            ctx.congestion_window = update.congestion_window
        if update.target_rate:
            ctx.rtt = update.target_rate.network_estimate.round_trip_time
            ctx.target_rate = update.target_rate.target_rate
        if update.in_probe_rtt is not None:
            # if ctx.burst_period > 0 and update.in_probe_rtt:
            #     logger.info(f'[{timestamp()}] Enter probe rtt')
            # if ctx.burst_period == 0 and not update.in_probe_rtt:
            #     logger.info(f'[{timestamp()}] Exit probe rtt')
            ctx.burst_period = 0 if update.in_probe_rtt else BURST_PERIOD


def next_send_time(pkg_size, ctx: Context):
    if FINE_LOG:
        global LOG_TS
        if timestamp() - LOG_TS >= MIN_LOG_PERIOD:
            LOG_TS = timestamp()
            logger.info(f'[{timestamp()}] pacing rate: {ctx.pacing_rate * 8}, '
                        f'target rate: {ctx.target_rate}, rtt: {ctx.rtt}')
    if ctx.congested():
        return ctx.last_send_time + kCongestedPacketInterval
    if ctx.pacing_rate:
        data_size = ctx.get_outstanding_data() - ctx.congestion_window - ctx.burst_period * ctx.pacing_rate
        data_size += pkg_size
        data_size = max(data_size, 0)
        pac_next = ctx.last_send_time + data_size / ctx.pacing_rate
        return min(ctx.last_process_time + kPausedProcessInterval, pac_next)
    return ctx.last_process_time + kPausedProcessInterval


def maybe_send(s: socket.socket, cc: CongestionControl, ctx: Context):
    now = timestamp()
    nst = next_send_time(ctx.get_pkg_size(True), ctx)
    if now >= nst:
        buf = bytearray(ctx.get_pkg_size())
        seq = ctx.send_seq
        buf[:SEQ_LENGTH] = seq.to_bytes(SEQ_LENGTH, byteorder=BYTE_ORDER)
        try:
            s.send(buf)
            ctx.in_flight.add(seq)
            ctx.packet_send_ts[ctx.send_seq] = now
            sent_packet = SentPacket()
            sent_packet.send_time = now
            sent_packet.size = len(buf)
            sent_packet.sequence_number = ctx.send_seq
            sent_packet.data_in_flight = len(ctx.in_flight) * ctx.get_pkg_size()
            ctx.sent_packet_record[ctx.send_seq] = sent_packet
            cc.on_sent_packet(sent_packet)
            ctx.send_seq += 1
            ctx.last_send_time = now
            ctx.last_process_time = now
            return len(buf)
        except BlockingIOError:
            return 0


def parse_args():
    parser = argparse.ArgumentParser(description='A UDP client that implements reliable transmission')
    parser.add_argument('-s', '--size', type=int, default=1460, help='UDP packet size')
    parser.add_argument('-t', '--time', type=int, default=15, help='Duration of the test, in seconds')
    parser.add_argument('-a', '--server', type=str, default='195.148.127.230', help='IP of the target server')
    parser.add_argument('-i', '--interval', type=int, default=10,
                        help='The interval of sending packets, in milliseconds')
    parser.add_argument('-c', '--congestion-control', type=str, choices=['bbr', 'static'], default='bbr',
                        help='The congestion control algorithm')
    parser.add_argument('-l', '--logger', default='/tmp/webrtc/logs/reliable_client.json',
                        help='Location of the dumped statics file')
    args = parser.parse_args()
    return args


def get_congestion_control(cc, ctx: Context) -> CongestionControl:
    if cc == 'static':
        return StaticPacing(ctx.interval)
    if cc == 'bbr':
        return BbrNetworkController(NetworkControllerConfig())


def main():
    args = parse_args()
    log_path = args.logger
    Path(os.path.dirname(log_path)).mkdir(parents=True, exist_ok=True)
    ctx = Context(args.time, args.interval, args.size)
    last_log = 0
    last_sequence = 0
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setblocking(0)
        s.connect((args.server, DEFAULT_UDP_PORT))
        cc = get_congestion_control(args.congestion_control, ctx)
        ctx.start_ts = timestamp()
        while timestamp() - ctx.start_ts < ctx.duration + 1:
            if (timestamp() - last_log) > LOG_PERIOD:
                send_rate = int((ctx.send_seq - last_sequence) * ctx.get_pkg_size(True) / LOG_PERIOD / 1024 * 8)
                pacing_rate = int(ctx.pacing_rate * 8 / 1024)
                target_rate = int(ctx.target_rate * 8 / 1024)
                packet_rate = int((ctx.send_seq - last_sequence) / LOG_PERIOD)
                rtt = int(ctx.rtt * 1000) if ctx.rtt != float('inf') else -1
                logger.info(f'{int(timestamp() - ctx.start_ts)}s has passed, snd r.: {send_rate} kbps, '
                            f'pac r.: {pacing_rate} kbps, tgt r.: {target_rate} kbps, rtt: {rtt} ms, '
                            f'pkg r.: {packet_rate}, data in flight: {ctx.get_outstanding_data()} bytes')
                last_log = timestamp()
                last_sequence = ctx.send_seq
            try:
                data, addr_ = s.recvfrom(2500)
                if is_ack(data):
                    on_packet_ack(get_seq(data), cc, ctx)
                else:
                    send_ack(data, s, addr_)
            except (BlockingIOError, ConnectionRefusedError) as e:
                pass
            try:
                if timestamp() - ctx.start_ts < ctx.duration:
                    maybe_send(s, cc, ctx)
            except BlockingIOError as e:
                pass
    statics = {'seq': ctx.send_seq, 'sent_ts': ctx.packet_send_ts[:ctx.send_seq].tolist(),
               'acked_ts': ctx.packet_recv_ts[:ctx.send_seq].tolist(),
               'config': {
                   'cc': args.congestion_control,
                   'pkg_size': args.size,
                   'duration': args.time,
               }}
    logger.info('Finished experiment, dumping logs')
    json.dump(statics, open(log_path, 'w+'))


if __name__ == '__main__':
    main()
