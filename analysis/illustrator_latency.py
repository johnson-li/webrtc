import json
import numpy as np
from sklearn.linear_model import LinearRegression
from utils.base import RESULT_DIAGRAM_PATH
import re
import os
import math
import argparse
from utils.plot import init_figure_wide
from matplotlib import pyplot as plt
from analysis.sync import parse_sync_log
from analysis.probing import parse_sync

# RESULT_DIR = os.path.expanduser('~/Workspace/webrtc-controller/results/2021:01:14-17:38:43')
# RESULT_DIR = os.path.expanduser('~/Workspace/webrtc-controller/results/2021:01:14-18:27:08')
# RESULT_DIR = '/tmp/webrtc/logs'
RESULT_DIR = os.path.expanduser('~/data/exp5/lab7/webrtc/logs')


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to visualize latency in detail.')
    parser.add_argument('-p', '--path', default=RESULT_DIR, help='Data path')
    parser.add_argument('-w', '--weight', default='yolov5s', help='The weight of YOLO',
                        choices=['yolov5x', 'yolov5s', 'yolov5l'])
    args = parser.parse_args()
    return args


def jitter(a):
    data = []
    med = np.median(a)
    return np.median(np.abs(a - med))
    # for i in range(len(a) - 1):
    #    data.append(abs(a[i] - a[i + 1]))
    # return np.median(data)


def main():
    args = parse_args()
    buffer = ''
    packets = []
    frame_delays = []
    frame_sizes = []
    weight_file = f"{args.path}/analysis_latency.{args.weight}.txt"
    lines = open(weight_file).readlines()
    reg: LinearRegression = parse_sync(path=args.path, plot=False)
    bandwidth = {'send': [], 'receive': [], 'start_ts': 0, 'end_ts': 0, 'bulk': 100}
    for line in lines:
        if line:
            if line.startswith("'======"):
                break
            if line[0] != '{':
                line = line.strip()
                buffer += line
            else:
                line = line.strip()
                if buffer:
                    data = eval(buffer)
                    for k, v in data.items():
                        assembled_timestamp = v.get('assembled_timestamp')
                        a = [p.get('receive_timestamp', 0) for p in v.get('packets', [])]
                        assembled_timestamp = max(a) if a else 0
                        encoded_timestamp = v.get('encoded_time')
                        decoded_timestamp = v.get('decoded_time')
                        if encoded_timestamp and assembled_timestamp:
                            frame_delays.append((encoded_timestamp, assembled_timestamp - encoded_timestamp))
                        for p in v.get('packets', []):
                            if 'size' in p and ('send_timestamp' in p or 'receive_timestamp' in p):
                                packets.append(
                                    (p.get('send_timestamp', None), p.get('receive_timestamp', None), p['size']))
                        if 'encoded_size' in v:
                            frame_sizes.append((v['frame_sequence'], v['encoded_size']))
                buffer = line
    bandwidth['start_ts'] = min([min(p[0], p[1]) for p in packets])
    bandwidth['end_ts'] = max([max(p[0], p[1]) for p in packets])
    bins = (bandwidth['end_ts'] - bandwidth['start_ts']) // bandwidth['bulk'] + 1
    bandwidth['send'] = np.zeros(bins)
    bandwidth['receive'] = np.zeros(bins)
    for p in packets:
        if p[0]:
            bin_send = (p[0] - bandwidth['start_ts']) // bandwidth['bulk']
            bandwidth['send'][bin_send] += p[2]
        if p[1]:
            bin_recv = (p[1] - bandwidth['start_ts']) // bandwidth['bulk']
            bandwidth['send'][bin_recv] += p[2]
    # lines = open(f"{RESULT_DIR}/network_client.log").readlines()
    # for line in lines:
    #     line = line.strip()
    #     if line and line.startswith('Down'):
    #         dl, up, ts = re.match('Downlink bandwidth: ([0-9]+) bps, uplink bandwidth: ([0-9]+) bps, at ([0-9]+)',
    #                               line).groups()
    #         bandwidth['send'].append((ts, dl, up))
    # lines = open(f"{RESULT_DIR}/network_server.log").readlines()
    # for line in lines:
    #     line = line.strip()
    #     if line and line.startswith('Down'):
    #         dl, up, ts = re.match('Downlink bandwidth: ([0-9]+) bps, uplink bandwidth: ([0-9]+) bps, at ([0-9]+)',
    #                               line).groups()
    #         bandwidth['receive'].append((ts, dl, up))

    # frame_delays = frame_delays[200:]
    # base = np.min(frame_delays)
    # frame_delays = (frame_delays - base) / 2 + base - 10

    print(f'Num. of packets: {len(packets)}')
    print(f'Num. of frames received: {len(frame_delays)}')
    print(f'Num. of frames sent: {len(frame_sizes)}')
    # packets = packets[20000:40000]
    # frame_delays = frame_delays[500:700]
    # frame_sizes = frame_sizes[500:700]
    print(f'Median of packet transmission delay: {np.median([p[1] - p[0] for p in packets if p[1] - p[0] < 1000])}')
    print(f'Min of packet transmission delay: {np.min([p[1] - p[0] for p in packets])}')
    print(f'Var of packet transmission delay: {np.std([p[1] - p[0] for p in packets if p[1] - p[0] < 1000])}')
    print(f'Median of frame transmission delay: {np.median([f[1] for f in frame_delays if f[1] < 1000])}')
    print(f'Min of frame transmission delay: {np.min([f[1] for f in frame_delays])}')
    print(f'Var of frame transmission delay: {np.std([f[1] for f in frame_delays if f[1] < 1000])}')
    print(f'Median of frame size: {np.median(frame_sizes)}')

    fig_size = (5, 3)

    # Draw packet delays
    packets.sort(key=lambda x: x[0])
    delays = [p[1] - p[0] - 10 for p in packets]
    fig, ax, font_size = init_figure_wide(figsize=fig_size)
    plt.plot([(p[0] - bandwidth['start_ts']) / 1000 for p in packets], delays, linewidth=1)
    plt.xlabel('Time (s)', size=font_size)
    plt.ylabel('Delay (ms)', size=font_size)
    # plt.xlim(55, 75)
    # plt.ylim(0, 100)
    plt.tight_layout(pad=.3)
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, 'timeline_packet_delay.pdf'))

    # Draw frame sizes
    frame_sizes.sort(key=lambda x: x[0])
    sizes = [s[1] / 1024 for s in frame_sizes]
    fig, ax, font_size = init_figure_wide()
    plt.plot(range(len(sizes)), sizes)
    plt.xlabel('Frames', size=font_size)
    plt.ylabel('Size (KB)', size=font_size)
    plt.tight_layout(pad=.3)
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, 'timeline_frame_size.pdf'))

    # Draw frame delays
    fig, ax, font_size = init_figure_wide(figsize=fig_size)
    print(frame_delays)
    plt.plot([(f[0] - bandwidth['start_ts']) / 1000 for f in frame_delays], [f[1] - 10 for f in frame_delays], linewidth=2)
    plt.xlabel('Time (s)', size=font_size)
    plt.ylabel('Delay (ms)', size=font_size)
    # plt.xlim(55, 75)
    plt.ylim(0, 100)
    plt.tight_layout(pad=.3)
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, 'timeline_frame_delay.pdf'))

    # Draw bandwidth
    ts = np.arange(bandwidth['send'].shape[0]) * bandwidth['bulk'] / 1000
    bd = bandwidth['send'] * 8 / bandwidth['bulk'] * 1000 / 1024 / 1024 / 2
    fig, ax, font_size = init_figure_wide(figsize=fig_size)
    plt.plot(ts, bd, linewidth=2)
    plt.xlabel('Time (s)', size=font_size)
    plt.ylabel('Bandwidth (Mbps)', size=font_size)
    # plt.xlim(55, 75)
    plt.ylim(0, 20)
    plt.tight_layout(pad=.3)
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, 'timeline_bandwidth.pdf'))


if __name__ == '__main__':
    main()
