import json
import numpy as np
import re
from matplotlib import pyplot as plt

DIR = '/home/lix16/Workspace/webrtc/results/latest'

def main():
    buffer = ''
    packets = []
    frame_sizes = []
    lines = open(f"{DIR}/analysis_latency.txt").readlines()
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
                        for p in v.get('packets', []):
                            if 'send_timestamp' in p and 'receive_timestamp' in p:
                                packets.append((p['send_timestamp'], p['receive_timestamp'] - p['send_timestamp']))
                        if 'encoded_size' in v:
                            frame_sizes.append((v['frame_sequence'], v['encoded_size']))
                buffer = line
    bandwidth = {'send': [], 'receive': []}
    lines = open(f"{DIR}/network_client.log").readlines()
    for line in lines:
        line = line.strip()
        if line and line.startswith('Down'):
            print(line)
            dl, up, ts = re.match('Downlink bandwidth: ([0-9]+) bps, uplink bandwidth: ([0-9]+) bps, at ([0-9]+)', line).groups()
            bandwidth['send'].append((ts, dl, up))
    lines = open(f"{DIR}/network_server.log").readlines()
    for line in lines:
        line = line.strip()
        if line and line.startswith('Down'):
            dl, up, ts = re.match('Downlink bandwidth: ([0-9]+) bps, uplink bandwidth: ([0-9]+) bps, at ([0-9]+)', line).groups()
            bandwidth['receive'].append((ts, dl, up))

    # Draw packet delays
    packets.sort(key=lambda x: x[0])
    delays = [p[1] for p in packets]
    print(delays)
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

    # Draw bandwidth
    send_ts = [int(d[0]) for d in bandwidth['send']]
    send_ul = [int(d[2]) for d in bandwidth['send']]
    recv_ts = [int(d[0]) - 1547603493 for d in bandwidth['receive']]
    recv_dl = [int(d[1]) for d in bandwidth['receive']]
    plt.plot(send_ts, send_ul)
    plt.plot(recv_ts, recv_dl)
    plt.title('Bandwidth')
    plt.xlabel('Time (ms)')
    plt.ylabel('Bandwidth (bps)')
    plt.legend(['Sender uplink', 'Receiver downlink'])
    plt.show()


if __name__ == '__main__':
    main()
