import argparse
import os
import numpy as np
import json
from matplotlib import pyplot as plt
from utils.base import RESULT_DIAGRAM_PATH


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


def draw_rtt(sent_ts, acked_ts):
    indexes = acked_ts > 0
    indexes_lost = acked_ts == 0
    x_lost = sent_ts[indexes_lost]
    x = sent_ts[indexes]
    y = (acked_ts[indexes] - sent_ts[indexes]) * 1000
    plt.figure()
    plt.plot(x, y)
    plt.plot(x_lost, np.ones_like(x_lost) * np.percentile(y, 20), 'x')
    plt.xlabel('Send time (s)')
    plt.ylabel('RTT (ms)')
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, 'reliable_rtt.png'), dpi=300)


def draw_bw(sent_ts, acked_ts, pkg_size):
    period = 0.06
    indexes = acked_ts > 0
    indexes_lost = acked_ts == 0
    x_lost = sent_ts[indexes_lost]
    sent_ts = sent_ts[indexes]
    acked_ts = acked_ts[indexes]
    start_ts, end_ts = sent_ts[0], sent_ts[-1]
    buckets = int((end_ts - start_ts) / period) + 1
    buckets = np.zeros((buckets, ))
    for v in sent_ts:
        buckets[int((v - start_ts) / period)] += pkg_size
    x = np.arange(0, len(buckets)) * period + start_ts
    y = buckets * 8 / period / 1024 / 1024
    plt.figure()
    plt.plot(x, y, '-o', ms=2)
    plt.plot(x_lost, np.ones_like(x_lost) * np.percentile(y, 30), 'x')
    plt.xlabel('Send time (s)')
    plt.ylabel('Bandwidth (Mbps)')
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, 'reliable_bw.png'), dpi=300)


def main():
    args = parse_args()
    data = json.load(open(args.file))
    sent_ts = np.array(data['sent_ts'])
    acked_ts = np.array(data['acked_ts'])
    draw_ts(sent_ts, acked_ts)
    draw_rtt(sent_ts, acked_ts)
    draw_bw(sent_ts, acked_ts, data['config']['pkg_size'])


if __name__ == '__main__':
    main()
