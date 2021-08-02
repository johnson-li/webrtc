import socket
import argparse
import os
import json
import numpy as np
from pathlib import Path
from utils2.logging import logging
from benchmark.cc.bbr import BbrNetworkController
from benchmark.cc.cc import CongestionControl, SentPacket, \
    NetworkControllerConfig, TransportPacketsFeedback, PacketResult
from benchmark.cc.static import StaticPacing
from benchmark.config import DEFAULT_UDP_PORT, SEQ_LENGTH, BYTE_ORDER, IP_HEADER_SIZE, \
    UDP_HEADER_SIZE, SINR_ARRAY_BUFFER_SIZE
from benchmark.reliable_utils import send_ack, timestamp, log_id, try_to_parse_ack
from multiprocessing import shared_memory

logger = logging.getLogger(__name__)
FINE_LOG = False
LOG_PERIOD = 1
LOG_TS = 0
MIN_LOG_PERIOD = 0.01
STATICS_SIZE = 100 * 1024 * 1024
kDefaultMinPacketLimit = 0.005
kCongestedPacketInterval = 0.5
kPausedProcessInterval = kCongestedPacketInterval
ENABLE_SINR_ENHANCEMENT = True


class Context(object):
    class Config(object):
        def __init__(self):
            self.BURST_PERIOD = 0
            self.BURST_RATIO = 2
            self.FPS = 0
            self.STREAM_BITRATE = 0  # in mbps

    class States(object):
        def __init__(self):
            self.bbr_state = []

    def __init__(self, duration, interval, pkg_size):
        self.config = Context.Config()
        self.states = Context.States()
        self.duration: int = duration
        self.interval: int = interval
        self.pkg_size: int = pkg_size
        self.packet_send_ts = np.zeros((STATICS_SIZE,), dtype=float)
        self.packet_ack_ts = np.zeros((STATICS_SIZE,), dtype=float)
        self.packet_recv_ts = np.zeros((STATICS_SIZE,), dtype=float)
        self.frame_first_ts = np.zeros((STATICS_SIZE,), dtype=float)
        self.frame_last_ts = np.zeros((STATICS_SIZE,), dtype=float)
        self.frame_seq = np.zeros((STATICS_SIZE,), dtype=float)
        self.pacing_rate_log = np.zeros((STATICS_SIZE, 3), dtype=float)
        self.pacing_ratio_log = np.zeros((STATICS_SIZE, 2), dtype=float)
        self.sent_packet_record = [None] * STATICS_SIZE
        self.send_seq = 0
        self.start_ts = 0
        self.pacing_rate_log_index = 0
        self.pacing_ratio_log_index = 0
        self.in_flight = set()
        self.last_send_time = 0
        self.last_process_time = 0
        self.pacing_rate = 0
        self.bandwidth_estimate = 0
        self.last_ack_sequence_num = 0
        self.congestion_window = float('inf')
        self.rtt = float('inf')
        self.target_rate = 0
        self.bursting = False
        self.bbr_state: BbrNetworkController.Mode = None
        self.pacing_ratio = 1
        self.pacing_ratio_period = 5
        self.pacing_ratio_start_ts = 0

    def get_pkg_size(self, ip_header=False):
        if ip_header:
            return self.pkg_size + IP_HEADER_SIZE + UDP_HEADER_SIZE
        return self.pkg_size

    def get_sent_data(self):
        return self.send_seq * self.get_pkg_size(True)

    def get_outstanding_data(self):
        return len(self.in_flight) * self.get_pkg_size(True)


def read_physical_layer_metrics():
    path = '/tmp/webrtc/logs/quectel'
    files = os.listdir(path)
    ids = [f.split('.')[0].split('_')[-1] for f in files]
    ids = [int(i) for i in ids if i != 'server']
    ids = sorted(ids, reverse=True)
    for i in ids:
        file = os.path.join(path, f'quectel_{i}.log')
        for line in open(file).readlines():
            if 'NR5G-NSA' in line:
                return int(line.split(',')[5]), i
    return None


def on_packet_ack(pkg_id, recv_ts, cc: CongestionControl, ctx: Context):
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
    ctx.packet_ack_ts[pkg_id] = now
    ctx.packet_recv_ts[pkg_id] = recv_ts
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
            ctx.bandwidth_estimate = update.target_rate.network_estimate.bandwidth
            ctx.pacing_rate_log[ctx.pacing_rate_log_index][0] = timestamp()
            ctx.pacing_rate_log[ctx.pacing_rate_log_index][1] = ctx.pacing_rate
            ctx.pacing_rate_log[ctx.pacing_rate_log_index][2] = update.target_rate.network_estimate.bandwidth
            ctx.pacing_rate_log_index += 1
        if update.congestion_window:
            ctx.congestion_window = update.congestion_window
        if update.target_rate:
            ctx.rtt = update.target_rate.network_estimate.round_trip_time
            ctx.target_rate = update.target_rate.target_rate
        if update.bbr_mode and ctx.bbr_state != update.bbr_mode:
            ctx.bbr_state = update.bbr_mode
            ctx.states.bbr_state.append((timestamp(), str(ctx.bbr_state)))


def next_send_time(pkg_size, ctx: Context, cc: CongestionControl):
    pacing_rate = ctx.pacing_rate
    if FINE_LOG:
        global LOG_TS
        if timestamp() - LOG_TS >= MIN_LOG_PERIOD:
            LOG_TS = timestamp()
            logger.info(f'[{timestamp()}] pacing rate: {pacing_rate * 8}, '
                        f'target rate: {ctx.target_rate}, rtt: {ctx.rtt}')
    if not pacing_rate:
        return ctx.last_process_time + kPausedProcessInterval
    if ENABLE_SINR_ENHANCEMENT:
        if timestamp() - ctx.pacing_ratio_start_ts <= cc._min_rtt * ctx.pacing_ratio_period:
            pacing_rate *= ctx.pacing_ratio
            # ctx.pacing_ratio_log[ctx.pacing_ratio_log_index] = (timestamp(), ctx.pacing_ratio)
            # ctx.pacing_ratio_log_index += 1
            # cc._max_bandwidth._window_length = 2
        else:
            # ctx.pacing_ratio_log[ctx.pacing_ratio_log_index] = (timestamp(), 1)
            # ctx.pacing_ratio_log_index += 1
            # cc._max_bandwidth._window_length = BbrNetworkController.kBandwidthWindowSize
            pass
    if not ctx.config.BURST_PERIOD:
        if ctx.get_outstanding_data() > ctx.congestion_window:
            return ctx.last_send_time + kCongestedPacketInterval
        if pacing_rate:
            pac_next = ctx.last_send_time + pkg_size / pacing_rate
            return min(ctx.last_process_time + kPausedProcessInterval, pac_next)
        return ctx.last_process_time + kPausedProcessInterval
    else:
        if ctx.bbr_state == BbrNetworkController.Mode.PROBE_BW:
            if ctx.bursting:
                if ctx.get_outstanding_data() > ctx.congestion_window + pacing_rate * ctx.config.BURST_PERIOD:
                    ctx.bursting = False
                    logger.info(f'[{timestamp()}] Exit bursting')
                    return ctx.last_send_time + kCongestedPacketInterval
                # print(pkg_size / ctx.pacing_rate / ctx.config.BURST_RATIO)
                return ctx.last_send_time + pkg_size / pacing_rate / ctx.config.BURST_RATIO
            else:
                if ctx.get_outstanding_data() > ctx.congestion_window:
                    return ctx.last_send_time + kCongestedPacketInterval
                ctx.bursting = True
                logger.info(f'[{timestamp()}] Enter bursting')
                pac_next = ctx.last_send_time + pkg_size / pacing_rate
                return min(ctx.last_process_time + kPausedProcessInterval, pac_next)
        else:
            if ctx.get_outstanding_data() > ctx.congestion_window:
                return ctx.last_send_time + kCongestedPacketInterval
            pac_next = ctx.last_send_time + pkg_size / pacing_rate
            return min(ctx.last_process_time + kPausedProcessInterval, pac_next)


def available_data(ctx: Context):
    if ctx.config.FPS and ctx.config.STREAM_BITRATE:
        frame_id = int((timestamp() - ctx.start_ts) * ctx.config.FPS)
        data_all = frame_id / ctx.config.FPS * ctx.config.STREAM_BITRATE * 1024 * 1024 / 8
        if data_all > ctx.get_sent_data():
            return frame_id
        return -1
    return 0


def maybe_send(s: socket.socket, cc: CongestionControl, ctx: Context):
    now = timestamp()
    nst = next_send_time(ctx.get_pkg_size(True), ctx, cc)
    frame_id = available_data(ctx)
    if now >= nst and frame_id >= 0:
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
            ctx.frame_seq[ctx.send_seq] = frame_id
            cc.on_sent_packet(sent_packet)
            ctx.send_seq += 1
            ctx.last_send_time = now
            ctx.last_process_time = now
            if not ctx.frame_first_ts[frame_id]:
                ctx.frame_first_ts[frame_id] = now
                # if frame_id > 0:
                #     print(f'Frame send time: {frame_id - 1}, '
                #           f'{ctx.frame_last_ts[frame_id - 1] - ctx.frame_first_ts[frame_id - 1]}')
            ctx.frame_last_ts[frame_id] = now
            # if ctx.bursting and ctx.get_outstanding_data() > ctx.congestion_window + ctx.pacing_rate * ctx.config.BURST_PERIOD:
            #     ctx.bursting = False
            # if not ctx.bursting and ctx.get_outstanding_data() <= ctx.congestion_window + ctx.pacing_rate * ctx.config.BURST_PERIOD:
            #     ctx.bursting = True
            return len(buf)
        except BlockingIOError:
            print('Packet send error')
            return 0


def parse_args():
    parser = argparse.ArgumentParser(description='A UDP client that implements reliable transmission')
    parser.add_argument('-s', '--size', type=int, default=1460, help='UDP packet size')
    parser.add_argument('-t', '--time', type=int, default=15, help='Duration of the test, in seconds')
    parser.add_argument('-a', '--server', type=str, default='195.148.127.230', help='IP of the target server')
    parser.add_argument('-b', '--burst-period', type=float, default=0, help='Time of the burst period, in seconds')
    parser.add_argument('-r', '--burst-ratio', type=float, default=0,
                        help='The ratio of increasing sending rate during burst period')
    parser.add_argument('-d', '--bitrate', type=float, default=0, help='The speed of generating data, in mbps')
    parser.add_argument('-f', '--fps', type=int, default=0, help='The FPS of generating data')
    parser.add_argument('-i', '--interval', type=int, default=10,
                        help='The interval of sending packets, in milliseconds')
    parser.add_argument('-c', '--congestion-control', type=str, choices=['bbr', 'static'], default='bbr',
                        help='The congestion control algorithm')
    parser.add_argument('-l', '--logger', default=f'/tmp/webrtc/logs/reliable_client_{log_id()}.json',
                        help='Location of the dumped statics file')
    args = parser.parse_args()
    return args


def get_congestion_control(cc, ctx: Context) -> CongestionControl:
    if cc == 'static':
        return StaticPacing(ctx.interval)
    if cc == 'bbr':
        return BbrNetworkController(NetworkControllerConfig())


def start_reliable_client():
    shm_a = shared_memory.SharedMemory(name='reliable', size=(SINR_ARRAY_BUFFER_SIZE + 1) * 4)
    args = parse_args()
    log_path = args.logger
    Path(os.path.dirname(log_path)).mkdir(parents=True, exist_ok=True)
    ctx = Context(args.time, args.interval, args.size)
    ctx.config.BURST_PERIOD = args.burst_period
    ctx.config.FPS = args.fps
    ctx.config.STREAM_BITRATE = args.bitrate
    ctx.config.BURST_RATIO = args.burst_ratio
    last_log = 0
    last_sequence = 0
    sinr_array_index_pre = 0
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setblocking(0)
        s.connect((args.server, DEFAULT_UDP_PORT))
        cc = get_congestion_control(args.congestion_control, ctx)
        ctx.start_ts = timestamp()
        while timestamp() - ctx.start_ts < ctx.duration + 1:
            sinr_array_index = int.from_bytes(shm_a.buf[: 4], byteorder=BYTE_ORDER)
            if sinr_array_index > sinr_array_index_pre:
                sinr_array_index_pre = sinr_array_index
                sinr_array = list()
                sinr = 0
                for i in range(SINR_ARRAY_BUFFER_SIZE):
                    ss = int.from_bytes(shm_a.buf[4 + 8 * (i % SINR_ARRAY_BUFFER_SIZE):
                                                  4 + 8 * (i % SINR_ARRAY_BUFFER_SIZE) + 4], byteorder=BYTE_ORDER)
                    sinr_array.append(ss)
                    if i == sinr_array_index % SINR_ARRAY_BUFFER_SIZE:
                        sinr = ss
                sinr_array = np.array(sinr_array, dtype=int)
                if ENABLE_SINR_ENHANCEMENT:
                    if sinr < 15:
                        cc._config.probe_bw_pacing_gain_offset = .05
                    else:
                        cc._config.probe_bw_pacing_gain_offset = .25
                    if sinr <= np.max(sinr_array) - 5:
                        ctx.pacing_ratio = .5
                        ctx.pacing_ratio_start_ts = timestamp()
                        # cc._pacing_gain_downgrade_at = timestamp()
                        # cc._pacing_gain_downgrade_gain = 8
                        # cc._min_rtt_timestamp = 0
                        logger.info(f'SINR downgrade detected: level 5')
                    elif sinr <= np.max(sinr_array) - 2:
                        ctx.pacing_ratio = .8
                        ctx.pacing_ratio_start_ts = timestamp()
                        # ctx.pacing_ratio = .1
                        # ctx.pacing_ratio_start_ts = timestamp()
                        # cc._pacing_gain_downgrade_at = timestamp()
                        # cc._pacing_gain_downgrade_gain = 8
                        # cc._min_rtt_timestamp = 0
                        logger.info(f'SINR downgrade detected: level 2')
                    elif sinr <= np.max(sinr_array) - 1:
                        ctx.pacing_ratio = .9
                        ctx.pacing_ratio_start_ts = timestamp()
                        logger.info(f'SINR downgrade detected: level 1')
                    elif sinr > np.min(sinr_array) + 5:
                        logger.info(
                            f'SINR upgrade detected: level 5, pacing gain: {cc._pacing_gain}, pr: {cc._pacing_rate / 1024 / 1024 * 8}')
                    elif sinr > np.min(sinr_array) + 2:
                        logger.info(
                            f'SINR upgrade detected: level 2, pacing gain: {cc._pacing_gain}, pr: {cc._pacing_rate / 1024 / 1024 * 8}')

            if (timestamp() - last_log) > LOG_PERIOD:
                send_rate = int((ctx.send_seq - last_sequence) * ctx.get_pkg_size(True) / LOG_PERIOD / 1024 * 8)
                pacing_rate = int(ctx.pacing_rate * 8 / 1024)
                target_rate = int(ctx.target_rate * 8 / 1024)
                bandwidth_estimate = int(ctx.bandwidth_estimate * 8 / 1024)
                packet_rate = int((ctx.send_seq - last_sequence) / LOG_PERIOD)
                rtt = int(ctx.rtt * 1000) if ctx.rtt != float('inf') else -1
                logger.info(f'{int(timestamp() - ctx.start_ts)}s has passed, snd r.: {send_rate} kbps, '
                            f'pac r.: {pacing_rate} kbps, tgt r.: {target_rate} kbps, rtt: {rtt} ms, '
                            f'bw est: {bandwidth_estimate} kbps, '
                            f'pkg r.: {packet_rate}, data in flight: {ctx.get_outstanding_data()} bytes')
                last_log = timestamp()
                last_sequence = ctx.send_seq
            try:
                data, addr_ = s.recvfrom(2500)
                is_ack, seq, recv_ts = try_to_parse_ack(data)
                if is_ack:
                    on_packet_ack(seq, recv_ts, cc, ctx)
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
               'acked_ts': ctx.packet_ack_ts[:ctx.send_seq].tolist(),
               'recv_ts': ctx.packet_recv_ts[:ctx.send_seq].tolist(),
               'frame_seq': ctx.frame_seq[:ctx.send_seq].tolist(),
               'bbr_state': ctx.states.bbr_state,
               'pacing_rate_log': ctx.pacing_rate_log[: ctx.pacing_rate_log_index].tolist(),
               'pacing_ratio_log': ctx.pacing_ratio_log[: ctx.pacing_ratio_log_index].tolist(),
               'config': {
                   'cc': args.congestion_control,
                   'pkg_size': args.size,
                   'duration': args.time,
                   'burst_period': ctx.config.BURST_PERIOD,
                   'burst_ratio': ctx.config.BURST_RATIO,
                   'bitrate': ctx.config.STREAM_BITRATE,
                   'fps': ctx.config.FPS
               }}
    logger.info('Finished experiment, dumping logs')
    json.dump(statics, open(log_path, 'w+'))


def main():
    start_reliable_client()


if __name__ == '__main__':
    main()
