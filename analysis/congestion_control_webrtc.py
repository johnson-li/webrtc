import argparse
import numpy as np
import matplotlib.pyplot as plt
from utils.base import RESULT_DIAGRAM_PATH
import os
from utils.base import DATA_PATH
from analysis.parser import parse_packets


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to visualize and analyse the congestion control in WebRTC.')
    parser.add_argument('-p', '--path', default=os.path.join(DATA_PATH, 'webrtc_exp4/latest'),
                        help='The directory of WebRTC logs')
    parser.add_argument('-g', '--granularity', default=200,
                        help='The granularity of calculating bandwidth usage, in milliseconds')
    args = parser.parse_args()
    return args


def parse_logs(path):
    sender_path = os.path.join(path, 'client2.log')
    receiver_path = os.path.join(path, 'client1.log')
    sender_sent_packets, sender_received_packets = parse_packets(sender_path)
    receiver_sent_packets, receiver_received_packets = parse_packets(receiver_path)
    return sender_sent_packets, sender_received_packets, receiver_sent_packets, receiver_received_packets


def illustrate(packets_list, granularity, name_list, title):
    start_ts = min([min([p['ts'] for p in ps]) for ps in packets_list])
    end_ts = max([max([p['ts'] for p in ps]) for ps in packets_list])
    time_slots = (end_ts - start_ts) // granularity + 1
    fig = plt.figure()
    for i, name in enumerate(name_list):
        bandwidth = []
        for _ in range(time_slots):
            bandwidth.append(0)
        packets = packets_list[i]
        for packet in packets:
            index = (packet['ts'] - start_ts) // granularity
            bandwidth[index] += packet['size']
        bandwidth = np.array(bandwidth) * 8 * 1000 / granularity / 1024 / 1024
        plt.plot(np.arange(0, time_slots, dtype=float) * granularity / 1000, bandwidth)
    if len(name_list) > 1:
        plt.legend(name_list)
    plt.xlabel('Time (s)')
    plt.ylabel('Bandwidth (mbps)')
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'webrtc_cc_{title}.pdf'))
    plt.show()


def main():
    args = parse_args()
    sender_sent_packets, sender_received_packets, receiver_sent_packets, receiver_received_packets = parse_logs(
        args.path)
    illustrate([sender_sent_packets, sender_received_packets], args.granularity, ['Sent', 'Received'], 'sender')
    illustrate([receiver_sent_packets, receiver_received_packets], args.granularity, ['Sent', 'Received'], 'receiver')


if __name__ == '__main__':
    main()
