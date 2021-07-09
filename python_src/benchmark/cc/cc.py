import math
from collections import deque


class NetworkEstimate(object):
    def __init__(self):
        self.at_time = float('inf')
        self.bandwidth = float('inf')
        self.round_trip_time = float('inf')
        self.bwe_period = float('inf')
        self.loss_rate_ratio: float = 0.0


class TargetTransferRate(object):
    def __init__(self):
        self.at_time = float('inf')
        self.network_estimate = NetworkEstimate()
        self.target_rate = 0
        self.stable_rate = 0
        self.cwnd_reduce_ratio: float = 0.0


class PacerConfig(object):
    def __init__(self):
        self.at_time = float('inf')
        self.data_window = float('inf')
        self.time_window = float('inf')
        self.pad_window = 0

    def data_rate(self):
        return self.data_window / self.time_window

    def pad_rate(self):
        return self.pad_window / self.time_window


class NetworkControlUpdate(object):
    def __init__(self):
        self.congestion_window: int = None
        self.pacer_config: PacerConfig = None
        self.probe_cluster_configs = list()
        self.target_rate = None


class TargetRateConstraints(object):
    def __init__(self):
        self.at_time = float('inf')
        self.min_data_rate = None
        self.max_data_rate = None
        self.starting_rate = None


class NetworkControllerConfig(object):
    def __init__(self):
        self.constraints: TargetRateConstraints = TargetRateConstraints()
        self.stream_based_config: StreamsConfig
        self.key_value_config: WebRtcKeyValueConfig


class BandwidthEstimate(object):
    def is_zero(self):
        pass


class ProcessInterval(object):
    def __init__(self):
        self.at_time: float = float('inf')
        self.pacer_queue = list()


class NetworkRouteChange(object):
    pass


class NetworkAvailbility(object):
    def __init__(self):
        self.at_time: float = float('inf')
        self.network_available: bool = False


class EntryWrapper(object):
    def __init__(self, data=None):
        self.data = data
        self.present: bool = data is not None


class PacketNumberIndexedQueue(object):
    def __init__(self):
        self._entries: deque = deque()
        self._number_of_present_entries: int = 0
        self._first_packet: int = 0

    def get_entry(self, packet_number: int):
        if packet_number < self._first_packet:
            return None
        offset = packet_number - self._first_packet
        if offset >= len(self._entries):
            return None
        return self._entries[offset]

    def is_empty(self):
        return self._number_of_present_entries == 0

    def emplace(self, packet_number: int, data):
        if self.is_empty():
            self._entries.append(EntryWrapper(data))
            self._number_of_present_entries = 1
            self._first_packet = packet_number
            return True
        if packet_number <= self.last_packet():
            return False
        offset = packet_number - self._first_packet
        if offset > len(self._entries):
            self._entries.resize(offset)
        self._number_of_present_entries += 1
        self._entries.append(EntryWrapper(data))
        return True

    def first_packet(self):
        return self._first_packet

    def last_packet(self):
        if self.is_empty():
            return 0
        return self._first_packet + len(self._entries) - 1

    def cleanup(self):
        while len(self._entries) > 0 and not self._entries[0].present:
            self._entries.popleft()
            self._first_packet += 1
        if len(self._entries) == 0:
            self._first_packet = 0

    def remove(self, packet_number: int):
        entry = self.get_entry(packet_number)
        if entry is None:
            return False
        entry.present = False
        self._number_of_present_entries -= 1
        if packet_number == self.first_packet():
            self.cleanup()
        return True


class PacedPacketInfo(object):
    kNotAProbe: int = -1
    send_bitrate_bps: int = -1
    probe_cluster_id: int = kNotAProbe
    probe_cluster_min_probes: int = -1
    probe_cluster_min_bytes: int = -1
    probe_cluster_bytes_sent: int = 0


class SentPacket(object):
    send_time: float = float('inf')
    size: int = 0
    prior_unacked_data: int = 0
    pacing_info: PacedPacketInfo = None
    audio: bool = False
    sequence_number: int = None
    data_in_flight: int = 0


class ReceivedPacket(object):
    send_time: int
    receive_time: int
    size: int


class RoundTripUpdate(object):
    receive_time: int
    round_trip_time: int
    smoothed: bool


class TransportLossReport(object):
    receive_time: int
    start_time: int
    end_time: int
    packets_lost_delta: int = 0
    packets_received_delta: int = 0


class CongestionControl(object):
    def __init__(self):
        pass

    def on_network_availbility(self, msg: NetworkAvailbility):
        raise NotImplementedError()

    def on_network_route_change(self, msg: NetworkRouteChange):
        raise NotImplementedError()

    def on_process_interval(self, msg: ProcessInterval):
        raise NotImplementedError()

    def on_remote_bitrate_report(self):
        raise NotImplementedError()

    def on_round_trip_time_update(self):
        raise NotImplementedError()

    def on_sent_packet(self, msg: SentPacket):
        raise NotImplementedError()

    def on_received_packet(self, msg: ReceivedPacket):
        raise NotImplementedError()

    def on_stream_config(self):
        raise NotImplementedError()

    def on_target_rate_constraints(self):
        raise NotImplementedError()

    def on_transport_loss_report(self):
        raise NotImplementedError()

    def on_transport_packets_feedback(self, feedback: "TransportPacketsFeedback"):
        raise NotImplementedError()

    def on_network_state_estimate(self):
        raise NotImplementedError()


class Packet(object):
    def __init__(self):
        self.send_time = 0
        self.sequence_number = 0
        self.size = 0
        self.data_in_flight = 0


class PacketResult(object):
    def __init__(self):
        self.sent_packet: SentPacket
        self.receive_time: float = float('inf')


class TransportPacketsFeedback(object):
    def __init__(self):
        self.feedback_time: float = float('inf')
        self.first_unacked_send_time: float = float('inf')
        self.data_in_flight: int = 0
        self.prior_in_flight: int = 0
        self.packet_feedbacks = list()
        self.sendless_arrival_times = list()

    def received_with_send_info(self):
        res = list()
        for fb in self.packet_feedbacks:
            if fb.receive_time < float('inf'):
                res.append(fb)
        return res

    def lost_with_send_info(self):
        res = list()
        for fb in self.packet_feedbacks:
            if fb.receive_time == float('inf'):
                res.append(fb)
        return res

    def packets_with_feedback(self):
        return self._packet_feedbacks

    def sorted_by_receive_time(self):
        res = list()
        for fb in self.packet_feedbacks:
            if fb.receive_time < float('inf'):
                res.append(fb)
        res = sorted(res, lambda x: (x.receive_time, x.sent_packet.send_time, x.sent_packet.sequence_number))
        return res


class ConnectionStateOnSentPacket(object):
    def __init__(self, sent_time, size, sampler: 'BandwidthSampler'):
        self.sent_time: int = sent_time
        self.size: int = size
        self.total_data_sent: int = sampler._total_data_sent
        self.total_data_sent_at_last_acked_packet: int = sampler._total_data_sent_at_last_acked_packet
        self.last_acked_packet_sent_time: int = sampler._last_acked_packet_sent_time
        self.last_acked_packet_ack_time: int = sampler._last_acked_packet_ack_time
        self.total_data_acked_at_the_last_acked_packet: int = sampler._total_data_acked
        self.is_app_limited: bool = sampler._is_app_limited


class WindowedFilter(object):
    class Sample(object):
        def __init__(self, data, ts):
            self._sample = data
            self._ts = ts

    def compare(self, a, b):
        if self._max_filter:
            return a >= b
        return b >= a

    def __init__(self, window_length, zero_value, zero_time, max_filter=True):
        self._window_length = window_length
        self._zero_value = zero_value
        self._max_filter = max_filter
        self._estimated = [WindowedFilter.Sample(zero_value, zero_time)] * 3

    def get_best(self):
        return self._estimated[0]._sample

    def get_second_best(self):
        return self._estimated[1]._sample

    def get_third_best(self):
        return self._estimated[2]._sample

    def update(self, new_sample, new_time):
        if self._estimated[0]._sample == self._zero_value or self.compare(new_sample,
                                                                          self._estimated[0]._sample) or new_time - \
                self._estimated[2]._ts > self._window_length:
            self.reset(new_sample, new_time)
            return
        if self.compare(new_sample, self._estimated[1]._sample):
            self._estimated[2] = self._estimated[1]
            self._estimated[1] = WindowedFilter.Sample(new_sample, new_time)
        elif self.compare(new_sample, self._estimated[2]._sample):
            self._estimated[2] = WindowedFilter.Sample(new_sample, new_time)
        if new_time - self._estimated[0]._ts > self._window_length:
            self._estimated[0] = self._estimated[1]
            self._estimated[1] = self._estimated[2]
            self._estimated[2] = WindowedFilter.Sample(new_sample, new_time)
            if new_time - self._estimated[0]._ts > self._window_length:
                self._estimated[0] = self._estimated[1]
                self._estimated[1] = self._estimated[2]
            return
        if self._estimated[1]._sample == self._estimated[0]._sample and new_time - self._estimated[
            1]._ts > self._window_length / 4:
            self._estimated[1] = WindowedFilter.Sample(new_sample, new_time)
            self._estimated[2] = WindowedFilter.Sample(new_sample, new_time)
            return
        if self._estimated[2]._sample == self._estimated[1]._sample and new_time - self._estimated[
            2]._ts > self._window_length / 2:
            self._estimated[2] = WindowedFilter.Sample(new_sample, new_time)
            return

    def reset(self, new_sample, new_time):
        self._estimated[0] = WindowedFilter.Sample(new_sample, new_time)
        self._estimated[1] = WindowedFilter.Sample(new_sample, new_time)
        self._estimated[2] = WindowedFilter.Sample(new_sample, new_time)


class BandwidthSample(object):
    def __init__(self):
        self.bandwidth: float = 0
        self.rtt: float = 0
        self.is_app_limited: bool = False


class BandwidthSampler(object):
    kMaxTrackedPackets = 10000

    def __init__(self):
        self._total_data_sent: int = 0
        self._total_data_acked: int = 0
        self._total_data_sent_at_last_acked_packet: int = 0
        self._last_acked_packet_sent_time: int = 0
        self._last_acked_packet_ack_time: int = 0
        self._last_sent_packet: int = 0
        self._is_app_limited: bool = False
        self._end_of_app_limited_phase: int = 0
        self._connection_state_map: PacketNumberIndexedQueue = PacketNumberIndexedQueue()

    def total_data_acked(self):
        return self._total_data_acked

    def on_packet_sent(self, sent_time: float, packet_number: int, data_size: int, data_in_flight: int):
        self._last_sent_packet = packet_number
        self._total_data_sent += data_size
        if data_in_flight == 0:
            self._last_acked_packet_ack_time = sent_time
            self._total_data_sent_at_last_acked_packet = self._total_data_sent
            self._last_acked_packet_sent_time = sent_time
        if not self._connection_state_map.is_empty() and packet_number > self._connection_state_map.last_packet() + BandwidthSampler.kMaxTrackedPackets:
            pass
        success = self._connection_state_map.emplace(packet_number,
                                                     ConnectionStateOnSentPacket(sent_time, data_size, self))

    def on_packet_acknowledged_inner(self, ack_time: float, packet_number: int,
                                     sent_packet: ConnectionStateOnSentPacket):
        self._total_data_acked += sent_packet.size
        self._total_data_sent_at_last_acked_packet = sent_packet.total_data_sent
        self._last_acked_packet_sent_time = sent_packet.sent_time
        self._last_acked_packet_ack_time = ack_time;
        if self._is_app_limited and packet_number > self._end_of_app_limited_phase:
            is_app_limited = False
        if not sent_packet.last_acked_packet_sent_time or not sent_packet.last_acked_packet_ack_time:
            return BandwidthSample()
        send_rate = float('inf')
        if sent_packet.sent_time > sent_packet.last_acked_packet_sent_time:
            sent_delta = sent_packet.total_data_sent - sent_packet.total_data_sent_at_last_acked_packet
            time_delta = sent_packet.sent_time - sent_packet.last_acked_packet_sent_time
            send_rate = sent_delta / time_delta
        if ack_time <= sent_packet.last_acked_packet_ack_time:
            return BandwidthSample()
        ack_delta = self._total_data_acked - sent_packet.total_data_acked_at_the_last_acked_packet
        time_delta = ack_time - sent_packet.last_acked_packet_ack_time
        ack_rate = ack_delta / time_delta
        sample = BandwidthSample()
        sample.bandwidth = min(send_rate, ack_rate)
        sample.rtt = ack_time - sent_packet.sent_time
        sample.is_app_limited = sent_packet.is_app_limited;
        return sample;

    def on_packet_acknowledged(self, ack_time: int, packet_number: int):
        sent_packet = self._connection_state_map.get_entry(packet_number)
        if sent_packet is None or not sent_packet.present:
            return BandwidthSample()
        sent_packet = sent_packet.data
        sample = self.on_packet_acknowledged_inner(ack_time, packet_number, sent_packet)
        self._connection_state_map.remove(packet_number)
        return sample

    def on_packet_lost(self, packet_number: int):
        self._connection_state_map.remove(packet_number)

    def on_app_limited(self):
        self._is_app_limited = True
        self._end_of_app_limited_phase = self._last_sent_packet

    def remove_obsolete_packets(self, least_unacked: int):
        while not self._connection_state_map.is_empty() and self._connection_state_map.first_packet() < least_unacked:
            self._connection_state_map.remove(self._connection_state_map.first_packet())

    def total_data_acked(self):
        return self._total_data_acked

    def is_app_limited(self):
        return self._is_app_limited

    def end_of_app_limited_phase(self):
        return self._end_of_app_limited_phase


class RttStats(object):
    kInitialRttMs = 100
    kAlpha = 0.125
    kOneMinusAlpha = 1 - kAlpha
    kBeta = 0.25
    kOneMinusBeta = 1 - kBeta
    kNumMicrosPerMilli = 1000

    def __init__(self):
        self.latest_rtt: float = 0
        self.min_rtt: float = 0
        self.smoothed_rtt: float = 0
        self.previous_srtt: float = 0
        self.mean_deviation: float = 0
        self.initial_rtt: float = RttStats.kInitialRttMs * RttStats.kNumMicrosPerMilli

    def update_rtt(self, send_delta, ack_delay, now):
        if send_delta == float('inf') or send_delta < 0:
            return
        if self.min_rtt == 0 or self.min_rtt > send_delta:
            self.min_rtt = send_delta
        rtt_sample = send_delta
        self.previous_srtt = self.smoothed_rtt
        if rtt_sample > ack_delay:
            rtt_sample -= ack_delay
        self.lastest_rtt = rtt_sample
        if self.smoothed_rtt == 0:
            self.smoothed_rtt = rtt_sample
            self.mean_deviation = rtt_sample / 2
        else:
            self.mean_deviation = RttStats.kOneMinusBeta * self.mean_deviation + RttStats.kBeta * abs(
                self.smoothed_rtt - rtt_sample)
            self.smoothed_rtt = RttStats.kOneMinusAlpha * self.smoothed_rtt + RttStats.kAlpha * rtt_sample


class LossRateFilter(object):
    kLimitNumPackets = 20
    kUpdateIntervalMs = 1000

    def __init__(self):
        self._lost_packets_since_last_loss_update = 0
        self._expected_packets_since_last_loss_update = 0
        self._loss_rate_estimate = 0.0
        self._next_loss_update_ms = 0

    def get_loss_rate(self):
        return self._loss_rate_estimate

    def update_with_loss_status(self, feedback_time, packets_sent, packets_lost):
        self._lost_packets_since_last_loss_update += packets_lost
        self._expected_packets_since_last_loss_update += packets_sent
        if feedback_time >= self._next_loss_update_ms and self._expected_packets_since_last_loss_update >= LossRateFilter.kLimitNumPackets:
            lost = self._lost_packets_since_last_loss_update
            expected = self._expected_packets_since_last_loss_update
            self._loss_rate_estimate = lost / expected
            self._next_loss_update_ms = feedback_time + LossRateFilter.kUpdateIntervalMs
            self._lost_packets_since_last_loss_update = 0
            self._expected_packets_since_last_loss_update = 0
