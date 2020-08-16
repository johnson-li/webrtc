import json
import numpy as np
import re
import os
import math
from matplotlib import pyplot as plt

RESULT_DIR = os.path.expanduser('~/Workspace/webrtc/results/2020:07:21-16:42:25')
SYNC_DIR = os.path.expanduser('~/Workspace/webrtc/results/sync')


def jitter(a):
    data = []
    med = np.median(a)
    return np.median(np.abs(a - med))
    #for i in range(len(a) - 1):
    #    data.append(abs(a[i] - a[i + 1]))
    #return np.median(data)


def main():
    buffer = ''
    packets = []
    frame_delays = []
    frame_sizes = []
    lines = open(f"{RESULT_DIR}/analysis_latency.txt").readlines()
    for line in lines:
        if line:
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
                        if encoded_timestamp and assembled_timestamp:
                            frame_delays.append(assembled_timestamp - encoded_timestamp)
                        for p in v.get('packets', []):
                            if 'send_timestamp' in p and 'receive_timestamp' in p:
                                packets.append((p['send_timestamp'], p['receive_timestamp'] - p['send_timestamp']))
                        if 'encoded_size' in v:
                            frame_sizes.append((v['frame_sequence'], v['encoded_size']))
                buffer = line
    bandwidth = {'send': [], 'receive': []}
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

    frame_delays = frame_delays[200:]
    base = np.min(frame_delays)
    frame_delays = (frame_delays - base) / 2 + base - 10
    print(np.median(frame_delays))
    print(np.min(frame_delays))
    print('jitter: ', jitter(frame_delays))

    sync_ts = []
    sync_rts = []
    for i in range(1, 101):
        f = os.path.join(SYNC_DIR, f'sync_{i}.log')
        for line in open(f).readlines():
            line = line.strip()
            if line.startswith('ts = '):
                ts = line[6: -1].split(',')[:-1]
                sync_ts.append(np.array([float(t) for t in ts]))
            if line.startswith('rts = '):
                rts = line[7: -1].split(',')[:-1]
                sync_rts.append(np.array([float(t) for t in rts]))
    with open(os.path.join(SYNC_DIR, 'sync_base.log')) as f:
        bias = int(f.readlines()[-1].split(' ')[-1])
    uplink_latency = []
    downlink_latency = []
    for i in range(len(sync_ts)):
        ts, rts = sync_ts[i], sync_rts[i]
        uplink_latency += (rts - ts - bias).tolist()
        downlink_latency += (ts[1:] - rts[:-1] + bias).tolist()
    print(np.median(uplink_latency))
    print('jitter: ', jitter(uplink_latency))
    print(np.median(downlink_latency))
    print('jitter: ', jitter(downlink_latency))

    # Draw packet delays
    packets.sort(key=lambda x: x[0])
    delays = [p[1] for p in packets]
    plt.title('Packet transmission delay')
    plt.plot(range(len(delays)), delays)
    plt.xlabel('Packets')
    plt.ylabel('Delay (ms)')
    plt.show()

    # Draw frame sizes
    frame_sizes.sort(key=lambda x: x[0])
    sizes = [s[1] for s in frame_sizes]
    plt.title('Frame sizes')
    plt.plot(range(len(sizes)), sizes)
    plt.xlabel('Frames')
    plt.ylabel('Size (bytes)')
    plt.show()

    # Draw frame delays
    plt.title('Frame delays')
    plt.plot(range(len(frame_delays)), frame_delays)
    plt.xlabel('Frames')
    plt.ylabel('Delay (ms)')
    plt.axis((0, len(frame_delays), 0, 400))
    plt.show()

    # Draw sync delays
    size = min(len(uplink_latency), len(downlink_latency))
    plt.title('Link delays')
    plt.plot(range(size), uplink_latency[:size], label='Uplink')
    plt.plot(range(size), downlink_latency[:size], label='Downlink')
    plt.xlabel('Packets')
    plt.ylabel('Delay (ms)')
    plt.legend()
    plt.show()

    # Draw bandwidth
    # send_ts = [int(d[0]) for d in bandwidth['send']]
    # send_ul = [int(d[2]) for d in bandwidth['send']]
    # recv_ts = [int(d[0]) - 1547603493 for d in bandwidth['receive']]
    # recv_dl = [int(d[1]) for d in bandwidth['receive']]
    # plt.plot(send_ts, send_ul)
    # plt.plot(recv_ts, recv_dl)
    # plt.title('Bandwidth')
    # plt.xlabel('Time (ms)')
    # plt.ylabel('Bandwidth (bps)')
    # plt.legend(['Sender uplink', 'Receiver downlink'])
    # plt.show()


if __name__ == '__main__':
    main()
