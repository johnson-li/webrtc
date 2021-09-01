import argparse
import os
import numpy as np
import json
from analysis.probing import parse_signal_strength, parse_handoff
from analysis.probing import parse_sync
from matplotlib import pyplot as plt
from experiment.base import RESULTS_PATH
from sklearn.linear_model import LinearRegression
from utils.base import RESULT_DIAGRAM_PATH

LOG_PATH = '/tmp/webrtc/logs'
LOG_PATH = os.path.join(RESULTS_PATH, 'bandwidth_adaption_4')
SUFFIX = ''


def latest_log():
    f = sorted(filter(lambda x: x.startswith('reliable_client_'), os.listdir(LOG_PATH)))[-2]
    return os.path.join(LOG_PATH, f)


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to analyse reliable transmission statics')
    parser.add_argument('-f', '--file', default=latest_log(), help='Path of the log file')
    return parser.parse_args()


def draw_ts(sent_ts, acked_ts, xrange=(0, 1)):
    s_ts, e_ts = sent_ts[0], sent_ts[-1]
    start_ts = s_ts + (e_ts - s_ts) * xrange[0]
    end_ts = s_ts + (e_ts - s_ts) * xrange[1]
    indexes = np.logical_and(np.logical_and(acked_ts > 0, sent_ts >= start_ts), sent_ts <= end_ts)
    indexes_lost = np.logical_and(np.logical_and(acked_ts == 0, sent_ts >= start_ts), sent_ts <= end_ts)
    x_lost = sent_ts[indexes_lost]
    x = sent_ts[indexes]
    y = acked_ts[indexes]
    plt.figure()
    plt.plot(x, y)
    plt.plot(x_lost, np.ones_like(x_lost) * np.percentile(y, 20), 'x')
    plt.xlabel('Send time (s)')
    plt.ylabel('Ack time (s)')
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'reliable_ts{SUFFIX}.png'), dpi=300)


def draw_latency(sent_ts, acked_ts, log_data, signal_data, metrics='sinr-nr', xrange=(0, 1), relative_y=True,
                 title='RTT', ylable='RTT (ms)', third_val=None):
    s_ts, e_ts = sent_ts[0], sent_ts[-1]
    start_ts = s_ts + (e_ts - s_ts) * xrange[0]
    end_ts = s_ts + (e_ts - s_ts) * xrange[1]
    indexes = np.logical_and(np.logical_and(acked_ts > 0, sent_ts >= start_ts), sent_ts <= end_ts)
    indexes_lost = np.logical_and(np.logical_and(acked_ts == 0, sent_ts >= start_ts), sent_ts <= end_ts)
    print(f'Packet loss rate: '
          f'{np.count_nonzero(indexes_lost) / (np.count_nonzero(indexes) + np.count_nonzero(indexes_lost))}')
    x_lost = sent_ts[indexes_lost]
    x = sent_ts[indexes]
    if relative_y:
        y = (acked_ts[indexes] - sent_ts[indexes]) * 1000
    else:
        y = acked_ts[indexes]
    fig, ax1 = plt.subplots(figsize=(6, 2))
    print(f'[{title}] Y range: {np.min(y)}, {np.max(y)}, medium: {np.median(y)}')
    ax1.plot(x, y)
    ax1.plot(x_lost, np.ones_like(x_lost) * np.percentile(y, 20), 'x')
    ax1.set_xlabel('Send time (s)                        ')
    ax1.set_ylabel(ylable)
    ax1.set_ylim((0, 120))
    ax1.set_xlim((np.min(x), np.max(x)))
    # ax1.set_xticks(np.arange(int(np.min(x) + 10), np.max(x), (np.max(x) - np.min(x)) / 4))
    if third_val is not None and third_val.shape[0] > 0:
        xx = third_val[:, 0]
        yy = third_val[:, 1] * np.max(y) * .8
        ax1.plot(xx, yy, linewidth=.5)
    if signal_data is not None:
        ts_list = [k for k, v in signal_data.items() if start_ts <= k <= end_ts and metrics in v]
        if ts_list:
            ax2 = ax1.twinx()
            ax2.plot(ts_list, [signal_data[t][metrics] for t in ts_list], 'y.-', linewidth=.4, ms=2)
            ax2.set_ylabel(metrics.upper())
            ax2.yaxis.label.set_color('y')
            # ax2.set_ylim([10, 40])
            ax2.tick_params(axis='y', labelcolor='y')
    fig.tight_layout()
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'reliable_{title}{SUFFIX}.pdf'), dpi=300)


def draw_bw(sent_ts, acked_ts, pkg_size, log_data, signal_data, metrics='sinr-nr', xrange=(0, 1)):
    s_ts, e_ts = sent_ts[0], sent_ts[-1]
    start_ts = s_ts + (e_ts - s_ts) * xrange[0]
    end_ts = s_ts + (e_ts - s_ts) * xrange[1]
    indexes = np.logical_and(np.logical_and(acked_ts > 0, sent_ts >= start_ts), sent_ts <= end_ts)
    indexes_lost = np.logical_and(np.logical_and(acked_ts == 0, sent_ts >= start_ts), sent_ts <= end_ts)
    period = 0.06
    x_lost = sent_ts[indexes_lost]
    sent_ts = sent_ts[indexes]
    acked_ts = acked_ts[indexes]
    buckets = int((end_ts - start_ts) / period) + 1
    buckets = np.zeros((buckets,))
    for v in sent_ts:
        buckets[int((v - start_ts) / period)] += pkg_size
    x = np.arange(0, len(buckets)) * period + start_ts
    y = buckets * 8 / period / 1024 / 1024
    plt.rcParams.update({'font.size': 14})
    fig, ax1 = plt.subplots(figsize=(6, 2))
    if log_data is not None:
        xx = log_data[:, 0]
        yy = log_data[:, 1] / 1024 / 1024
        indexes = np.logical_and(xx >= start_ts, xx <= end_ts)
        xx, yy = xx[indexes], yy[indexes]
        ax1.plot(xx, yy)
    ax1.plot(x, y, linewidth=2)
    # ax1.plot(x_lost, np.ones_like(x_lost) * np.percentile(y, 30), 'x')
    ax1.set_xlabel('Send time (s)')
    ax1.set_ylabel('Bandwidth\n(Mbps)')
    if log_data is not None:
        ax1.legend(['Estimated bandwidth', 'Sending rate', ])
    if signal_data is not None:
        ts_list = [k for k, v in signal_data.items() if start_ts <= k <= end_ts and metrics in v]
        ax2 = ax1.twinx()
        ax2.plot(ts_list, [signal_data[t][metrics] for t in ts_list], 'y', linewidth=1)
        ax2.set_ylabel(metrics.upper())
        ax2.yaxis.label.set_color('y')
        # ax2.set_ylim([10, 40])
        ax2.tick_params(axis='y', labelcolor='y')
    fig.tight_layout()
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'reliable_bw{SUFFIX}.pdf'), dpi=300)


def parse_log(log_path='/tmp/rc.log'):
    if not os.path.exists(log_path):
        return None
    data = {}
    for line in open(log_path).readlines():
        line = line.strip()
        if 'pacing rate: ' in line and 'target rate: ' in line:
            line = line[15:]
            array = line.split(', ')
            ts = float(array[0].split('] ')[0])
            array[0] = array[0].split('] ')[1]
            pacing_rate = float(array[0].split(': ')[1])
            data[ts] = pacing_rate
    data0 = np.zeros((len(data), 2))
    keys = list(sorted(data.keys()))
    for i in range(len(data)):
        data0[i, 0] = keys[i]
        data0[i, 1] = data[data0[i, 0]]
    return data0


def draw_frame_latency(sent_ts, recv_ts, frame_seq, xrange=(0, 1)):
    s_ts, e_ts = sent_ts[0], sent_ts[-1]
    start_ts = s_ts + (e_ts - s_ts) * xrange[0]
    end_ts = s_ts + (e_ts - s_ts) * xrange[1]
    frame_ts = np.zeros((max(frame_seq) + 1, 3), dtype=float)
    frame_ts[:, 0] += 99999999999
    for i in np.arange(0, len(sent_ts)):
        seq = frame_seq[i]
        frame_ts[seq][0] = min(frame_ts[seq][0], sent_ts[i])
        frame_ts[seq][1] = max(frame_ts[seq][1], sent_ts[i])
        frame_ts[seq][2] = max(frame_ts[seq][2], recv_ts[i])
    frame_delay = frame_ts[:, 2] - frame_ts[:, 0]
    frame_delay = frame_delay[frame_delay > 0]
    send_delay = frame_ts[:, 1] - frame_ts[:, 0]
    send_delay = send_delay[send_delay > 0]
    return frame_delay, send_delay


def draw_bw_lat(x1, y1, x2, y2):
    fig, ax1 = plt.subplots(figsize=(6, 2))
    bias = np.min(x1)
    x1 -= bias
    x2 -= bias
    ax1.plot(x1, y1)
    ax1.set_xlabel('Send time (s)')
    ax1.set_ylabel('Estimated\nbandwidth (Mbps)')
    ax1.set_ylim((-100, 120))
    ax1.set_xlim((np.min(x1), np.max(x1)))
    # ax1.set_xticks(np.arange(int(np.min(x) + 10), np.max(x), (np.max(x) - np.min(x)) / 4))
    ax2 = ax1.twinx()
    ax2.plot(x2, y2, 'y')
    ax2.set_ylabel('Packet transmission\nlatency (ms)')
    ax2.yaxis.label.set_color('y')
    ax2.set_ylim([0, 150])
    ax2.tick_params(axis='y', labelcolor='y')
    fig.tight_layout()
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'reliable_bw_lat{SUFFIX}.pdf'), dpi=300)


def single():
    DRAW_SIGNAL = True
    DRAW_LOG = False
    args = parse_args()
    data = json.load(open(args.file))
    print(f'burst period: {data["config"]["burst_period"]}')
    log_data = parse_log() if DRAW_LOG else None
    reg: LinearRegression = parse_sync(plot=False, path=LOG_PATH)
    sent_ts = np.array(data['sent_ts'])
    acked_ts = np.array(data['acked_ts'])
    recv_ts = np.array(data['recv_ts'])
    pacing_log = np.array(data['pacing_rate_log'])
    pacing_ratio_log = np.array(data['pacing_ratio_log'])
    recv_ts = reg.predict(np.expand_dims(recv_ts, axis=1))
    signal_data = parse_signal_strength(log_path=LOG_PATH) if DRAW_SIGNAL else None
    metrics = 'sinr-nr'
    xrange = [0, 1]
    # xrange = [.3, .6]
    draw_bw_lat(pacing_log[:, 0], pacing_log[:, 1] / 1024 / 1024 * 8,
                sent_ts[recv_ts > 0], (recv_ts[recv_ts > 0] - sent_ts[recv_ts > 0]) * 1000)
    draw_latency(sent_ts, acked_ts, log_data, signal_data, metrics=metrics,
                 xrange=xrange, title='rtt', third_val=pacing_ratio_log)
    draw_latency(sent_ts, recv_ts, log_data, signal_data, metrics=metrics, third_val=pacing_ratio_log,
                 xrange=xrange, title='pkg_trans', ylable='Packet transmission\nlatency (ms)')
    draw_latency(pacing_log[:, 0], pacing_log[:, 1] / 1024 / 1024 * 8, log_data, signal_data, metrics=metrics,
                 third_val=pacing_ratio_log,
                 xrange=xrange, title='estimated_bandwidth', ylable='Estimated\nbandwidth (Mbps)', relative_y=False)
    draw_bw(sent_ts, acked_ts, data['config']['pkg_size'], log_data, signal_data, metrics=metrics, xrange=xrange)
    draw_ts(sent_ts, acked_ts, xrange=xrange)
    # draw_frame_latency(sent_ts, recv_ts, frame_seq, xrange, 10)


def mesh():
    # bitrate -> burst ratio -> [send delay, packet latency, frame latency]
    res = {}
    percentile = 95

    for log_path in [os.path.expanduser('~/Workspace/webrtc-controller/results/burst1'),
                     os.path.expanduser('~/Workspace/webrtc-controller/results/burst2'),
                     os.path.expanduser('~/Workspace/webrtc-controller/results/burst3')]:
        reg: LinearRegression = parse_sync(plot=False, path=log_path)
        ids = []
        for f in os.listdir(log_path):
            if f.startswith('reliable_client_'):
                log_id = f.split('.')[0].split('_')[-1]
                ids.append(log_id)
        ids = sorted(ids)
        for log_id in ids:
            f = os.path.join(log_path, f'reliable_client_{log_id}.json')
            data = json.load(open(f))
            burst_period = data['config']['burst_period']
            burst_ratio = data['config']['burst_ratio']
            bitrate = data['config']['bitrate']
            sent_ts = np.array(data['sent_ts'])
            acked_ts = np.array(data['acked_ts'])
            recv_ts = np.array(data['recv_ts'])
            loss_ratio = np.count_nonzero(recv_ts <= 0) / recv_ts.shape[0]
            frame_seq = np.array(data['frame_seq'], dtype=int)
            recv_ts = reg.predict(np.expand_dims(recv_ts, axis=1))
            packet_latency = recv_ts - sent_ts
            frame_latency, send_delay = draw_frame_latency(sent_ts, recv_ts, frame_seq)
            print(f'Burst period: {burst_period}, burst ratio: {burst_ratio}, '
                  f'bitrate: {bitrate}, frame latency: {np.percentile(frame_latency, percentile)}, '
                  f'packet latency: {np.percentile(packet_latency, percentile)}, '
                  f'send delay: {np.percentile(send_delay, percentile)}, loss ratio: {loss_ratio}')
            res.setdefault(bitrate, {})
            send_delay = np.percentile(send_delay, percentile)
            frame_latency = np.percentile(frame_latency, percentile)
            packet_latency = np.percentile(packet_latency, percentile)
            if burst_ratio not in res[bitrate] or frame_latency < res[bitrate][burst_ratio][2]:
                res[bitrate][burst_ratio] = (send_delay, packet_latency, frame_latency)

    fig = plt.figure(figsize=np.array([3, 2]) * 2)
    font = {'size': 16}

    # matplotlib.rc('font', **font)
    bitrates = list(sorted(res.keys()))
    for br in bitrates:
        x = list()
        y = list()
        v = res[br]
        for ratio in list(sorted(v.keys())):
            x.append(ratio)
            y.append(v[ratio][2])
        plt.plot(x, np.array(y) * 1000, linewidth=2)
    plt.xlabel('Burst ratio')
    plt.ylabel('Frame transmission\n latency (ms)')
    plt.legend(['5 Mbps', '10 Mbps', '20 Mbps'])
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'burst_ratio_effect_{percentile}{SUFFIX}.png'), dpi=600)


def main():
    single()
    # mesh()


if __name__ == '__main__':
    main()
