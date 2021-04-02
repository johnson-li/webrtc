import os
import numpy as np
import json
import matplotlib.pyplot as plt
from experiment.base import RESULTS_PATH, DATA_PATH

PROBING_PATH = os.path.join(RESULTS_PATH, "probing")
PROBING_PATH = '/tmp/webrtc/logs'


def analyse(packets, title):
    keys = packets.keys()
    keys = sorted(list(keys))
    delays = []
    lost = []
    x = []
    for key in keys:
        if 'received_ts' in packets[key]:
            x.append(key)
            delays.append(packets[key]['received_ts'] - packets[key]['sent_ts'])
        else:
            lost.append([key, 0])
    y = delays
    y -= np.min(y)
    plt.plot(x, y)
    plt.plot([l[0] for l in lost], [l[1] for l in lost], 'x')
    plt.ylabel('Packet Transmission Latency (ms)')
    plt.xlabel('Packet sequence')
    plt.title(title)
    plt.show()


def convert(records):
    return [{'timestamp': r[0] * 1000, 'sequence': r[1]} for r in records]


def main():
    path = os.path.join(PROBING_PATH, "probing_2021-03-21-15-47-45.json")
    client_path = os.path.join(PROBING_PATH, "probing_client.log")
    server_path = os.path.join(PROBING_PATH, "server.log")
    client_data = json.load(open(client_path))
    server_data = json.load(open(server_path))
    # path = os.path.join(PROBING_PATH, "probing_2021-03-06-18-24-25.json")
    # data = json.load(open(path))
    # client_sent = data['clientResult']['sent']
    # client_received = data['clientResult']['received']
    # server_sent = data['serverResult']['sent']
    # server_received = data['serverResult']['received']
    client_sent = convert(client_data['probing_sent'])
    client_received = convert(client_data['probing_received'])
    server_sent = server_data['probing_sent']
    server_received = server_data['probing_received']
    print(f'Uplink packets: {len(client_sent)}, {client_sent[-1]["sequence"] + 1}')
    print(f'Downlink packets: {len(server_sent)}, {server_sent[-1]["sequence"] + 1}')
    print(f'Packet loss ratio, uplink: {"%.2f" % (100 * len(server_received) / len(client_sent))}%, '
          f'downlink {"%.2f" % (100 * len(client_received) / len(server_sent))}%')
    uplink_packets = {}
    downlink_packets = {}

    def feed(sender, receiver, result):
        for p in sender:
            result[p['sequence']] = {'sent_ts': p['timestamp']}
        for p in receiver:
            if p['sequence'] in result:
                result[p['sequence']]['received_ts'] = p['timestamp']
            else:
                print(f'Sequence: {p["sequence"]} not seen in sender')

    feed(client_sent, server_received, uplink_packets)
    feed(server_sent, client_received, downlink_packets)
    analyse(uplink_packets, 'uplink')
    analyse(downlink_packets, 'downlink')


if __name__ == '__main__':
    main()
