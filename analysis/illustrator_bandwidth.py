import os
import argparse
import numpy as np
from analysis.parser import parse_results_latency
import matplotlib.pyplot as plt
from utils.base import RESULT_DIAGRAM_PATH


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to illustrate the bandwidth.')
    parser.add_argument('-f', '--folder', help='The folder of the experiment logs')
    parser.add_argument('-b', '--bin', default=200, type=int,
                        help='The granularity of the time sequences, in millisecond')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    folder = args.folder
    res = parse_results_latency(folder)
    sent_packets = []
    received_packets = []
    for k, v in res.items():
        if 'packets' not in v:
            continue
        packets = v['packets']
        for packet in packets:
            if 'send_timestamp' in packet:
                sent_packets.append((packet['send_timestamp'], packet['size']))
            if 'receive_timestamp' in packet:
                received_packets.append((packet['receive_timestamp'], packet['size']))
    sent_packets = sorted(sent_packets, key=lambda x: x[0])
    received_packets = sorted(received_packets, key=lambda x: x[0])
    start_ts = min(sent_packets[0][0], received_packets[0][0])
    end_ts = max(sent_packets[-1][0], received_packets[-1][0])
    period = args.bin
    bins = (end_ts - start_ts) // period + 1
    sent_data = np.zeros((bins,))
    received_data = np.zeros((bins,))
    for p in sent_packets:
        b = (p[0] - start_ts) // period
        sent_data[b] += p[1]
    for p in received_packets:
        b = (p[0] - start_ts) // period
        received_data[b] += p[1]
    x = np.array([i * period for i in range(bins)])
    plt.plot(x / 1000, sent_data * 8 * 1000 / 1024 / 1024 / period)
    plt.plot(x / 1000, received_data * 8 * 1000 / 1024 / 1024 / period)
    plt.xlabel('Time (s)')
    plt.ylabel('Bandwidth (Mbps)')
    plt.legend(['Sending', 'Receiving'])
    # plt.show()
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'bandwidth.png'), dpi=600)


if __name__ == '__main__':
    main()
