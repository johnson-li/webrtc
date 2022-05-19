import random
import copy
import time
from benchmark.cc.cc import *
from enum import Enum


def logging_with_ts(msg):
    print(f'[{time.time()}] {msg}')


class BbrNetworkController(CongestionControl):
    kBbrRttVariationWeight = 0.0
    kProbeBWCongestionWindowGain = 2.0
    kMaxPacketSize = 1452
    kDefaultTCPMSS = 1460
    kMaxSegmentSize = kDefaultTCPMSS
    kHighGain = 2.885
    kStartupAfterLossGain = 1.5
    kDrainGain = 1.0 / kHighGain
    kGainCycleLength = 8
    kBandwidthWindowSize = kGainCycleLength + 2
    kMinRttExpirySeconds = 10
    kProbeRttTime = 0.2  # Johnson
    kStartupGrowthTarget = 1.25
    kSimilarMinRttThreshold = 1.125
    kInitialBandwidthKbps = 300
    kInitialCongestionWindowPackets = 32
    kDefaultMinCongestionWindowPackets = 4
    kDefaultMaxCongestionWindowPackets = 2000

    class Mode(Enum):
        STARTUP = 1  # Startup phase of the connection.
        DRAIN = 2  # After achieving the highest possible bandwidth during the startup, lower the pacing rate in order to drain the queue.
        PROBE_BW = 3  # Cruising mode
        PROBE_RTT = 4  # Temporarily slow down sending in order to empty the buffer and measure the real minimum RTT

    class RecoveryState(Enum):
        NOT_IN_RECOVERY = 1  # Do not limit
        CONSERVATION = 2  # Allow an extra outstanding byte for each byte acknowledged
        MEDIUM_GROWTH = 3  # Allow 1.5 extra outstanding bytes for each byte acknowledged
        GROWTH = 4  # Allow two extra outstanding bytes for each byte acknowledged (slow start)

    class BbrControllerConfig(object):
        def __init__(self):
            self.probe_bw_pacing_gain_offset: float = .25  # Johnson: fix for low quality wireless network
            self.encoder_rate_gain: float = 1
            self.encoder_rate_gain_in_probe_rtt: float = 1
            self.exit_startup_rtt_threshold: float = float('inf')
            self.initial_congestion_window: float = \
                BbrNetworkController.kInitialCongestionWindowPackets * BbrNetworkController.kDefaultTCPMSS
            self.min_congestion_window: float = \
                BbrNetworkController.kDefaultMinCongestionWindowPackets * BbrNetworkController.kDefaultTCPMSS
            self.max_congestion_window: float = \
                BbrNetworkController.kDefaultMaxCongestionWindowPackets * BbrNetworkController.kDefaultTCPMSS
            self.probe_rtt_congestion_window_gain: float = .75
            self.pacing_rate_as_target: bool = False
            self.exit_startup_on_loss: bool = True
            self.num_startup_rtts: int = 3
            self.rate_based_recovery: bool = False
            self.max_aggregation_bytes_multiplier: float = 0
            self.slower_startup: bool = False
            self.rate_based_startup: bool = False
            self.initial_conservation_in_startup: BbrNetworkController.RecoveryState = \
                BbrNetworkController.RecoveryState.CONSERVATION
            self.fully_drain_queue: bool = False
            self.max_ack_height_window_multiplier: float = 1
            self.probe_rtt_based_on_bdp: bool = False
            self.probe_rtt_skipped_if_similar_rtt: bool = False
            self.probe_rtt_disabled_if_app_limited: bool = False

        @staticmethod
        def from_trial():
            return BbrNetworkController.BbrControllerConfig()

    def __init__(self, config: NetworkControllerConfig):
        super(BbrNetworkController, self).__init__()
        self._config: BbrNetworkController.BbrControllerConfig = BbrNetworkController.BbrControllerConfig.from_trial()
        self._rtt_stats: RttStats = RttStats()
        self._loss_rate: LossRateFilter = LossRateFilter()
        self._mode: BbrNetworkController.Mode = BbrNetworkController.Mode.STARTUP
        self._sampler: BandwidthSampler = BandwidthSampler()
        self._round_trip_count = 0
        self._last_sent_packet: int = 0
        self._current_round_trip_end: int = 0
        self._max_bandwidth = WindowedFilter(BbrNetworkController.kBandwidthWindowSize, 0, 0)
        self._default_bandwidth: int = BbrNetworkController.kInitialBandwidthKbps
        self._max_ack_height = WindowedFilter(BbrNetworkController.kBandwidthWindowSize, 0, 0)
        self._aggregation_epoch_start_time: int = None
        self._aggregation_epoch_bytes: int = 0
        self._bytes_acked_since_queue_drained: int = 0
        self._max_aggregation_bytes_multiplier: int = 0
        self._min_rtt: int = 0
        self._last_rtt: int = 0
        self._min_rtt_timestamp: float = float('inf')
        self._congestion_window: float = self._config.initial_congestion_window
        self._initial_congestion_window: float = self._config.initial_congestion_window
        self._min_congestion_window: float = self._config.min_congestion_window
        self._max_congestion_window: float = self._config.max_congestion_window
        self._pacing_rate: float = 300000 / 8
        self._pacing_gain: float = 1
        self._congestion_window_gain: float = BbrNetworkController.kProbeBWCongestionWindowGain
        self._congestion_window_gain_constant: float = BbrNetworkController.kProbeBWCongestionWindowGain
        self._rtt_variance_weight: float = BbrNetworkController.kBbrRttVariationWeight
        self._cycle_current_offset: int = 0
        self._last_cycle_start: float = float('-inf')
        self._is_at_full_bandwidth: bool = False
        self._rounds_without_bandwidth_gain = 0
        self._bandwidth_at_last_round: int = 0
        self._exiting_quiescence: bool = False
        self._exit_probe_rtt_at: float = None
        self._probe_rtt_round_passed: bool = False
        self._last_sample_is_app_limited: bool = False
        self._recovery_state: BbrNetworkController.RecoveryState = BbrNetworkController.RecoveryState.NOT_IN_RECOVERY
        self._end_recovery_at: float = None
        self._recovery_window: float = self._max_congestion_window
        self._app_limited_since_last_probe_rtt: bool = False
        self._min_rtt_since_last_probe_rtt: float = float('-inf')
        self._pacing_gain_downgrade_gain = 0
        self._pacing_gain_downgrade_at = 0
        if config.constraints.starting_rate:
            self._default_bandwidth = config.constraints.starting_rate
        self._constraints: TargetRateConstraints = config.constraints
        self.reset()

    def reset(self):
        self._round_trip_count = 0
        self._rounds_without_bandwidth_gain = 0
        if self._config.num_startup_rtts > 0:
            self._is_at_full_bandwidth = False
            self.enter_startup_mode()
        else:
            self._is_at_full_bandwidth = True
            self.enter_probe_bandwidth_mode(self._constraints.at_time)

    def create_rate_update(self, at_time: float):
        bandwidth = self.bandwidth_estimate()
        if bandwidth == 0:
            bandwidth = self._default_bandwidth
        rtt = self.get_min_rtt()
        pacing_rate = self.pacing_rate()
        if self._config.pacing_rate_as_target:
            target_rate = pacing_rate
        else:
            target_rate = bandwidth
        if self._mode == BbrNetworkController.Mode.PROBE_RTT:
            target_rate = target_rate * self._config.encoder_rate_gain_in_probe_rtt
        else:
            target_rate = target_rate * self._config.encoder_rate_gain
        target_rate = min(target_rate, pacing_rate)
        if self._constraints:
            if self._constraints.max_data_rate:
                target_rate = min(target_rate, self._constraints.max_data_rate)
                pacing_rate = min(pacing_rate, self._constraints.max_data_rate)
            if self._constraints.min_data_rate:
                target_rate = max(target_rate, self._constraints.min_data_rate)
                pacing_rate = max(pacing_rate, self._constraints.min_data_rate)
        update = NetworkControlUpdate()
        target_rate_msg = TargetTransferRate()
        target_rate_msg.network_estimate.bandwidth = bandwidth
        target_rate_msg.network_estimate.at_time = at_time
        target_rate_msg.network_estimate.round_trip_time = rtt
        target_rate_msg.network_estimate.loss_rate_ratio = 0
        target_rate_msg.network_estimate.bwe_period = rtt * BbrNetworkController.kGainCycleLength
        target_rate_msg.target_rate = target_rate
        target_rate_msg.at_time = at_time
        update.target_rate = target_rate_msg
        pacer_config = PacerConfig()
        pacer_config.time_window = rtt * 0.25
        pacer_config.data_window = pacer_config.time_window * pacing_rate
        if self.is_probing_for_more_bandwidth():
            pacer_config.pad_window = pacer_config.data_window
        else:
            pacer_config.pad_window = 0
        pacer_config.at_time = at_time
        update.pacer_config = pacer_config
        update.congestion_window = self.get_congestion_window()
        update.bbr_mode = self._mode
        return update

    def on_network_availbility(self, msg: NetworkAvailbility):
        self.reset()
        self._rtt_stats.on_connection_migration()
        return self.create_rate_update(msg.at_time)

    def on_network_route_change(self, msg: NetworkRouteChange):
        self._constraints = msg.constraints
        self.reset()
        if msg.constraints.starting_rate:
            self._default_bandwidth = msg.constraints.starting_rate
        self._rtt_stats.on_connection_migration()
        return self.create_rate_update(msg.at_time)

    def on_process_interval(self, msg: ProcessInterval):
        return self.create_rate_update(msg.at_time)

    def on_streams_config(self):
        return

    def on_target_rate_constraints(self, msg: TargetRateConstraints):
        self._constraints = msg
        return self.create_rate_update(msg.at_time)

    def in_slow_start(self):
        return self._mode == BbrNetworkController.Mode.STARTUP

    def on_sent_packet(self, pkg: SentPacket):
        self._last_sent_packet = pkg.sequence_number
        if pkg.data_in_flight == 0 and self._sampler.is_app_limited():
            self._exiting_quiescence = True
        if not self._aggregation_epoch_start_time:
            self._aggregation_epoch_start_time = pkg.send_time
        self._sampler.on_packet_sent(pkg.send_time, pkg.sequence_number, pkg.size, pkg.data_in_flight)

    def can_send(self, bytes_in_flight: int):
        return bytes_in_flight < self.get_congestion_window()

    def pacing_rate(self):
        if self._pacing_rate == 0:
            return BbrNetworkController.kHighGain * self._initial_congestion_window / self.get_min_rtt()
        return self._pacing_rate

    def bandwidth_estimate(self):
        return self._max_bandwidth.get_best()

    def get_congestion_window(self):
        if self._mode == BbrNetworkController.Mode.PROBE_RTT:
            return self.probe_rtt_congestion_window()
        if self.in_recovery() and not self._config.rate_based_recovery and not (
                self._config.rate_based_startup and self._mode == BbrNetworkController.Mode.STARTUP):
            return min(self._congestion_window, self._recovery_window)
        return self._congestion_window

    def is_in_pacing_gain_downgrade(self, now):
        return now - self._pacing_gain_downgrade_at <= self._min_rtt * 30

    def get_pacing_gain(self, round_offset: int, now: int):
        if round_offset == 0:
            return 1 + self._config.probe_bw_pacing_gain_offset
        elif round_offset == 1:
            return 1 - self._config.probe_bw_pacing_gain_offset
        elif self.is_in_pacing_gain_downgrade(now) and round_offset <= self._pacing_gain_downgrade_gain + 1:
            return 1 - self._config.probe_bw_pacing_gain_offset
        return 1

    def in_recovery(self):
        return self._recovery_state != BbrNetworkController.RecoveryState.NOT_IN_RECOVERY

    def is_probing_for_more_bandwidth(self):
        return (self._mode == BbrNetworkController.Mode.PROBE_BW and self._pacing_gain > 1) or \
               self._mode == BbrNetworkController.Mode.STARTUP

    def on_transport_packets_feedback(self, feedback: TransportPacketsFeedback):
        if len(feedback.packet_feedbacks) == 0:
            return
        feedback_recv_time = feedback.feedback_time
        last_sent_packet = feedback.packet_feedbacks[-1].sent_packet
        send_time = last_sent_packet.send_time
        send_delta = feedback_recv_time - send_time
        self._rtt_stats.update_rtt(send_delta, 0, feedback_recv_time)
        total_data_acked_before = self._sampler.total_data_acked()
        is_round_start = False
        min_rtt_expired = False
        lost_packets = feedback.lost_with_send_info()
        self.discard_lost_packets(lost_packets)
        acked_packets = feedback.received_with_send_info()
        packets_sent = len(lost_packets) + len(acked_packets)
        packets_lost = len(lost_packets)
        self._loss_rate.update_with_loss_status(feedback.feedback_time, packets_sent, packets_lost)
        if len(acked_packets) > 0:
            last_acked_packet = acked_packets[0].sent_packet.sequence_number
            is_round_start = self.update_round_trip_counter(last_acked_packet)
            min_rtt_expired = self.update_bandwidth_and_min_rtt(feedback.feedback_time, acked_packets)
            self.update_recovery_state(last_acked_packet, len(lost_packets) > 0, is_round_start)
            data_acked = self._sampler.total_data_acked() - total_data_acked_before
            self.update_ack_aggregation_bytes(feedback.feedback_time, data_acked)
            if self._max_aggregation_bytes_multiplier > 0:
                if feedback.data_in_flight <= 1.25 * self.get_target_congestion_window(self._pacing_gain):
                    self._bytes_acked_since_queue_drained = 0
                else:
                    self._bytes_acked_since_queue_drained += data_acked
        if self._mode == BbrNetworkController.Mode.PROBE_BW:
            self.update_gain_cycle_phase(feedback.feedback_time, feedback.prior_in_flight, len(lost_packets) > 0)
        if is_round_start and not self._is_at_full_bandwidth:
            self.check_if_full_bandwidth_reached()
        self.maybe_exit_startup_or_drain(feedback)
        self.maybe_enter_or_exit_probe_rtt(feedback, is_round_start, min_rtt_expired)
        data_acked = self._sampler.total_data_acked() - total_data_acked_before
        data_lost = 0
        for packet in lost_packets:
            data_lost += packet.sent_packet.size
        self.calculate_pacing_rate()
        self.calculate_congestion_window(data_acked)
        self.calculate_recovery_window(data_acked, data_lost, feedback.data_in_flight)
        if len(acked_packets) > 0:
            self._sampler.remove_obsolete_packets(acked_packets[-1].sent_packet.sequence_number)
        return self.create_rate_update(feedback.feedback_time)

    def get_min_rtt(self):
        if self._min_rtt == 0:
            return self._rtt_stats.initial_rtt
        return self._min_rtt

    def get_target_congestion_window(self, gain: float):
        bdp = self.get_min_rtt() * self.bandwidth_estimate()
        congestion_window = gain * bdp
        if congestion_window == 0:
            congestion_window = gain * self._initial_congestion_window
        return max(congestion_window, self._min_congestion_window)

    def probe_rtt_congestion_window(self):
        if self._config.probe_rtt_based_on_bdp:
            return self.get_target_congestion_window(self._config.probe_rtt_congestion_window_gain)
        return self._min_congestion_window

    def enter_startup_mode(self):
        logging_with_ts('Enter startup mode')
        self._mode = BbrNetworkController.Mode.STARTUP
        self._pacing_gain = BbrNetworkController.kHighGain
        self._congestion_window_gain = BbrNetworkController.kHighGain

    def enter_probe_bandwidth_mode(self, now):
        logging_with_ts('Enter probe bandwidth mode')
        self._mode = BbrNetworkController.Mode.PROBE_BW
        self._congestion_window_gain = self._congestion_window_gain_constant
        self._cycle_current_offset = random.randint(0, BbrNetworkController.kGainCycleLength - 2)
        if self._cycle_current_offset >= 1:
            self._cycle_current_offset += 1
        self._last_cycle_start = now
        self._pacing_gain = self.get_pacing_gain(self._cycle_current_offset, now)

    def discard_lost_packets(self, lost_packets):
        for packet in lost_packets:
            self._sampler.on_packet_lost(packet.sent_packet.sequence_number)

    def update_round_trip_counter(self, last_acked_packet):
        if last_acked_packet > self._current_round_trip_end:
            self._round_trip_count += 1
            self._current_round_trip_end = self._last_sent_packet
            return True
        return False

    def update_bandwidth_and_min_rtt(self, now, acked_packets):
        sample_rtt = float('inf')
        for packet in acked_packets:
            bandwidth_sample = self._sampler.on_packet_acknowledged(now, packet.sent_packet.sequence_number)
            self._last_sample_is_app_limited = bandwidth_sample.is_app_limited
            if bandwidth_sample.rtt != 0:
                sample_rtt = min(sample_rtt, bandwidth_sample.rtt)
            if not bandwidth_sample.is_app_limited or bandwidth_sample.bandwidth > self.bandwidth_estimate():
                # print(bandwidth_sample.bandwidth / 1024 / 1024)
                self._max_bandwidth.update(bandwidth_sample.bandwidth, self._round_trip_count)
        if sample_rtt == float('inf'):
            return False
        self._last_rtt = sample_rtt
        self._min_rtt_since_last_probe_rtt = min(self._min_rtt_since_last_probe_rtt, sample_rtt)
        kMinRttExpiry = BbrNetworkController.kMinRttExpirySeconds
        min_rtt_expired = self._min_rtt != 0 and now > (self._min_rtt_timestamp + kMinRttExpiry)
        if min_rtt_expired or sample_rtt < self._min_rtt or self._min_rtt == 0:
            if self.should_extend_min_rtt_expiry():
                min_rtt_expired = False
            else:
                self._min_rtt = sample_rtt
            self._min_rtt_timestamp = now
            self._min_rtt_since_last_probe_rtt = float('inf')
            self._app_limited_since_last_probe_rtt = False
        return min_rtt_expired

    def should_extend_min_rtt_expiry(self):
        if self._config.probe_rtt_disabled_if_app_limited and self._app_limited_since_last_probe_rtt:
            return True
        min_rtt_increased_since_last_probe = \
            self._min_rtt_since_last_probe_rtt > self._min_rtt * BbrNetworkController.kSimilarMinRttThreshold
        if self._config.probe_rtt_skipped_if_similar_rtt and \
                self._app_limited_since_last_probe_rtt and not min_rtt_increased_since_last_probe:
            return True
        return False

    def update_gain_cycle_phase(self, now, prior_in_flight, has_losses: bool):
        should_advance_gain_cycling = now - self._last_cycle_start > self.get_min_rtt()
        if self._pacing_gain > 1 and not has_losses and \
                prior_in_flight < self.get_target_congestion_window(self._pacing_gain):
            should_advance_gain_cycling = False
        if self._pacing_gain < 1 and prior_in_flight <= self.get_target_congestion_window(1):
            should_advance_gain_cycling = True
        if should_advance_gain_cycling:
            self._cycle_current_offset = (self._cycle_current_offset + 1) % BbrNetworkController.kGainCycleLength
            self._last_cycle_start = now
            if self._config.fully_drain_queue and self._pacing_gain < 1 and self.get_pacing_gain(
                    self._cycle_current_offset, now) == 1 and prior_in_flight > self.get_target_congestion_window(1):
                return
            self._pacing_gain = self.get_pacing_gain(self._cycle_current_offset, now)

    def check_if_full_bandwidth_reached(self):
        if self._last_sample_is_app_limited:
            return
        target = self._bandwidth_at_last_round * BbrNetworkController.kStartupGrowthTarget
        if self.bandwidth_estimate() >= target:
            self._bandwidth_at_last_round = self.bandwidth_estimate()
            self._rounds_without_bandwidth_gain = 0
            return
        self._rounds_without_bandwidth_gain += 1
        if self._rounds_without_bandwidth_gain >= self._config.num_startup_rtts or \
                (self._config.exit_startup_on_loss and self.in_recovery()):
            self._is_at_full_bandwidth = True

    def maybe_exit_startup_or_drain(self, feedback: TransportPacketsFeedback):
        exit_threshold = self._config.exit_startup_rtt_threshold
        rtt_delta = self._last_rtt - self._min_rtt
        if self._mode == BbrNetworkController.Mode.STARTUP and \
                (self._is_at_full_bandwidth or rtt_delta > exit_threshold):
            logging_with_ts('Enter drain mode')
            self._mode = BbrNetworkController.Mode.DRAIN
            self._pacing_gain = BbrNetworkController.kDrainGain
            self._congestion_window_gain = BbrNetworkController.kHighGain
        if self._mode == BbrNetworkController.Mode.DRAIN and \
                feedback.data_in_flight <= self.get_target_congestion_window(1):
            self.enter_probe_bandwidth_mode(feedback.feedback_time)

    def maybe_enter_or_exit_probe_rtt(self, feedback: TransportPacketsFeedback,
                                      is_round_start: bool, min_rtt_expired: bool):
        if min_rtt_expired and not self._exiting_quiescence and self._mode != BbrNetworkController.Mode.PROBE_RTT:
            logging_with_ts('Enter probe rtt mode')
            self._mode = BbrNetworkController.Mode.PROBE_RTT
            self._pacing_gain = 1
            self._exit_probe_rtt_at = None
        if self._mode == BbrNetworkController.Mode.PROBE_RTT:
            self._sampler.on_app_limited()
            if not self._exit_probe_rtt_at:
                if feedback.data_in_flight < self.probe_rtt_congestion_window() + BbrNetworkController.kMaxPacketSize:
                    self._exit_probe_rtt_at = feedback.feedback_time + BbrNetworkController.kProbeRttTime
                    self._probe_rtt_round_passed = False
            else:
                if is_round_start:
                    self._probe_rtt_round_passed = True
                if feedback.feedback_time >= self._exit_probe_rtt_at and self._probe_rtt_round_passed:
                    self._min_rtt_timestamp = feedback.feedback_time
                    if not self._is_at_full_bandwidth:
                        self.enter_startup_mode()
                    else:
                        self.enter_probe_bandwidth_mode(feedback.feedback_time)
        self._exiting_quiescence = False

    def update_recovery_state(self, last_acked_packet: int, has_losses: bool, is_round_start: bool):
        if has_losses:
            self._end_recovery_at = self._last_sent_packet
        if self._recovery_state == BbrNetworkController.RecoveryState.NOT_IN_RECOVERY:
            if has_losses:
                self._recovery_state = BbrNetworkController.RecoveryState.CONSERVATION
                if self._mode == BbrNetworkController.Mode.STARTUP:
                    self._recovery_state = self._config.initial_conservation_in_startup
                self._recovery_window = 0
                self._current_round_trip_end = self._last_sent_packet
        elif self._recovery_state in \
                [BbrNetworkController.RecoveryState.CONSERVATION, BbrNetworkController.RecoveryState.MEDIUM_GROWTH]:
            if is_round_start:
                self._recovery_state = BbrNetworkController.RecoveryState.GROWTH
        elif self._recovery_state == BbrNetworkController.RecoveryState.GROWTH:
            if not has_losses and (not self._end_recovery_at or last_acked_packet > self._end_recovery_at):
                self._recovery_state = BbrNetworkController.RecoveryState.NOT_IN_RECOVERY

    def update_ack_aggregation_bytes(self, ack_time: float, newly_acked_bytes: int):
        if not self._aggregation_epoch_start_time:
            return
        expected_bytes_acked = self._max_bandwidth.get_best() * (ack_time - self._aggregation_epoch_start_time)
        if self._aggregation_epoch_bytes <= expected_bytes_acked:
            self._aggregation_epoch_bytes = newly_acked_bytes
            self._aggregation_epoch_start_time = ack_time
            return
        self._aggregation_epoch_bytes += newly_acked_bytes
        self._max_ack_height.update(self._aggregation_epoch_bytes - expected_bytes_acked, self._round_trip_count)

    def calculate_pacing_rate(self):
        if self.bandwidth_estimate() == 0:
            return
        target_rate = self._pacing_gain * self.bandwidth_estimate()
        if self._config.rate_based_recovery and self.in_recovery():
            self._pacing_rate = self._pacing_gain * self._max_bandiwdth.get_third_best()
        if self._is_at_full_bandwidth:
            self._pacing_rate = target_rate
            return
        if self._pacing_rate == 0 and self._rtt_stats.min_rtt != 0:
            self._pacing_rate = self._initial_congestion_window / self._rtt_stats.min_rtt
            return
        has_ever_detected_loss = self._end_recovery_at is not None
        if self._config.slower_startup and has_ever_detected_loss:
            self._pacing_rate = BbrNetworkController.kStartupAfterLossGain * self.bandwidth_estimate()
            return
        self._pacing_rate = max(self._pacing_rate, target_rate)

    def calculate_congestion_window(self, bytes_acked: int):
        if self._mode == BbrNetworkController.Mode.PROBE_RTT:
            return
        target_window = self.get_target_congestion_window(self._congestion_window_gain)
        if self._rtt_variance_weight > 0 and self.bandwidth_estimate() != 0:
            target_window += self._rtt_variance_weight * self._rtt_stats.mean_deviation * self.bandwidth_estimate()
        elif self._max_aggregation_bytes_multiplier > 0 and self._is_at_full_bandwidth:
            if self._max_aggregation_bytes_multiplier * self._max_ack_height.get_best() > \
                    self._bytes_acked_since_queue_drained / 2:
                target_window += self._max_aggregation_bytes_multiplier * self._max_ack_height.get_best() - self._bytes_acked_since_queue_drained / 2;
        elif self._is_at_full_bandwidth:
            target_window += self._max_ack_height.get_best()
        if self._is_at_full_bandwidth:
            self._congestion_window = min(target_window, self._congestion_window + bytes_acked)
        elif self._congestion_window < target_window or \
                self._sampler.total_data_acked() < self._initial_congestion_window:
            self._congestion_window += bytes_acked
        self._congestion_window = max(self._congestion_window, self._min_congestion_window)
        self._congestion_window = min(self._congestion_window, self._max_congestion_window)

    def calculate_recovery_window(self, bytes_acked: int, bytes_lost: int, bytes_in_flight):
        if self._config.rate_based_recovery or \
                (self._config.rate_based_startup and self._mode == BbrNetworkController.Mode.STARTUP):
            return
        if self._recovery_state == BbrNetworkController.RecoveryState.NOT_IN_RECOVERY:
            return
        if self._recovery_window == 0:
            self._recovery_window = bytes_in_flight + bytes_acked
            self._recovery_window = max(self._min_congestion_window, self._recovery_window)
            return
        if self._recovery_window >= bytes_lost:
            self._recovery_window -= bytes_lost
        else:
            self._recovery_window = BbrNetworkController.kMaxSegmentSize
        if self._recovery_state == BbrNetworkController.RecoveryState.GROWTH:
            self._recovery_window += bytes_acked
        elif self._recovery_state == BbrNetworkController.RecoveryState.MEDIUM_GROWTH:
            self._recovery_window += bytes_acked / 2
        self._recovery_window = max(self._recovery_window, bytes_in_flight + bytes_acked)
        self._recovery_window = max(self._min_congestion_window, self._recovery_window)

    def on_application_limited(self, bytes_in_flight: int):
        if bytes_in_flight >= self.get_congestion_window():
            return
        self._app_limited_since_last_probe_rtt = True
        self._sampler.on_app_limited()


def test():
    config = NetworkControllerConfig()
    bbr = BbrNetworkController(config)
    msg1 = SentPacket()
    msg1.sequence_number = 1
    msg1.send_time = time.time()
    msg1.size = 1000
    msg1.pacing_info = PacedPacketInfo()
    msg2 = SentPacket()
    msg2.sequence_number = 2
    msg2.send_time = time.time()
    msg2.size = 1000
    msg2.pacing_info = PacedPacketInfo()
    bbr.on_sent_packet(msg1)
    bbr.on_sent_packet(msg2)

    fb1 = TransportPacketsFeedback()
    fb1.feedback_time = time.time()
    pr1 = PacketResult()
    pr1.receive_time = time.time()
    pr1.sent_packet = copy.copy(msg1)
    fb1.packet_feedbacks.append(pr1)
    bbr.on_transport_packets_feedback(fb1)
    fb2 = TransportPacketsFeedback()
    fb2.feedback_time = time.time()
    pr2 = PacketResult()
    pr2.receive_time = time.time()
    pr2.sent_packet = copy.copy(msg2)
    fb2.packet_feedbacks.append(pr2)
    bbr.on_transport_packets_feedback(fb2)


if __name__ == '__main__':
    test()
