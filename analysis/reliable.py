import argparse
import os
import numpy as np
import json
from matplotlib import pyplot as plt
from utils.base import RESULT_DIAGRAM_PATH
from analysis.probing import parse_signal_strength, parse_handoff


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to analyse reliable transmission statics')
    parser.add_argument('-f', '--file', default='/tmp/webrtc/logs/reliable_client.json', help='Path of the log file')
    return parser.parse_args()


def draw_ts(sent_ts, acked_ts):
    indexes = acked_ts > 0
    indexes_lost = acked_ts == 0
    x_lost = sent_ts[indexes_lost]
    x = sent_ts[indexes]
    y = acked_ts[indexes]
    plt.figure()
    plt.plot(x, y)
    plt.plot(x_lost, np.ones_like(x_lost) * np.percentile(y, 20), 'x')
    plt.xlabel('Send time (s)')
    plt.ylabel('Ack time (s)')
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, 'reliable_ts.png'), dpi=300)


def draw_rtt(sent_ts, acked_ts, log_data, signal_data, metrics='sinr-nr', xrange=(0, 1)):
    start_ts, end_ts = sent_ts[0], sent_ts[-1]
    start_ts = start_ts + (end_ts - start_ts) * xrange[0]
    end_ts = start_ts + (end_ts - start_ts) * xrange[1]
    indexes = np.logical_and(np.logical_and(acked_ts > 0, sent_ts >= start_ts), sent_ts <= end_ts)
    indexes_lost = np.logical_and(np.logical_and(acked_ts == 0, sent_ts >= start_ts), sent_ts <= end_ts)
    print(f'Packet loss rate: '
          f'{np.count_nonzero(indexes_lost) / (np.count_nonzero(indexes) + np.count_nonzero(indexes_lost))}')
    x_lost = sent_ts[indexes_lost]
    x = sent_ts[indexes]
    y = (acked_ts[indexes] - sent_ts[indexes]) * 1000
    fig, ax1 = plt.subplots()
    ax1.plot(x, y)
    ax1.plot(x_lost, np.ones_like(x_lost) * np.percentile(y, 20), 'x')
    ax1.set_xlabel('Send time (s)')
    ax1.set_ylabel('RTT (ms)')
    if signal_data is not None:
        ts_list = [k for k, v in signal_data.items() if start_ts <= k <= end_ts and metrics in v]
        ax2 = ax1.twinx()
        ax2.plot(ts_list, [signal_data[t][metrics] for t in ts_list], 'y.-', linewidth=.4, ms=2)
        ax2.set_ylabel(metrics.upper())
        ax2.yaxis.label.set_color('y')
        # ax2.set_ylim([10, 40])
        ax2.tick_params(axis='y', labelcolor='y')
    fig.tight_layout()
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, 'reliable_rtt.png'), dpi=300)


def draw_bw(sent_ts, acked_ts, pkg_size, log_data, signal_data, metrics='sinr-nr', xrange=(0, 1)):
    start_ts, end_ts = sent_ts[0], sent_ts[-1]
    start_ts = start_ts + (end_ts - start_ts) * xrange[0]
    end_ts = start_ts + (end_ts - start_ts) * xrange[1]
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
    fig, ax1 = plt.subplots()
    if log_data is not None:
        xx = log_data[:, 0]
        yy = log_data[:, 1] / 1024 / 1024
        indexes = np.logical_and(xx >= start_ts, xx <= end_ts)
        xx, yy = xx[indexes], yy[indexes]
        ax1.plot(xx, yy)
    ax1.plot(x, y, '-o', ms=2)
    ax1.plot(x_lost, np.ones_like(x_lost) * np.percentile(y, 30), 'x')
    ax1.set_xlabel('Send time (s)')
    ax1.set_ylabel('Bandwidth (Mbps)')
    if log_data is not None:
        ax1.legend(['Estimated bandwidth', 'Sending rate', ])
    if signal_data is not None:
        ts_list = [k for k, v in signal_data.items() if start_ts <= k <= end_ts and metrics in v]
        ax2 = ax1.twinx()
        ax2.plot(ts_list, [signal_data[t][metrics] for t in ts_list], 'y.-', linewidth=.4, ms=2)
        ax2.set_ylabel(metrics.upper())
        ax2.yaxis.label.set_color('y')
        # ax2.set_ylim([10, 40])
        ax2.tick_params(axis='y', labelcolor='y')
    fig.tight_layout()
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, 'reliable_bw.png'), dpi=300)


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


def main():
    DRAW_SIGNAL = True
    DRAW_LOG = False
    args = parse_args()
    data = json.load(open(args.file))
    log_data = parse_log() if DRAW_LOG else None
    sent_ts = np.array(data['sent_ts'])
    acked_ts = np.array(data['acked_ts'])
    signal_data = parse_signal_strength(log_path='/tmp/webrtc/logs/quectel') if DRAW_SIGNAL else None
    # draw_ts(sent_ts, acked_ts)
    metrics = 'sinr-nr'
    # xrange = [0.1, 0.2]
    xrange = [0, 1]
    draw_rtt(sent_ts, acked_ts, log_data, signal_data, metrics=metrics, xrange=xrange)
    draw_bw(sent_ts, acked_ts, data['config']['pkg_size'], log_data, signal_data, metrics=metrics, xrange=xrange)


if __name__ == '__main__':
    main()
