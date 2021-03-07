import os
import numpy as np
import json
import matplotlib.pyplot as plt
from experiment.base import RESULTS_PATH, DATA_PATH

PROBING_PATH = os.path.join(RESULTS_PATH, "probing")


def analyse(packets):
    keys = packets.keys()
    keys = sorted(list(keys))
    delays = []
    x = []
    for key in keys:
        if 'received_ts' in packets[key]:
            x.append(key)
            delays.append(packets[key]['received_ts'] - packets[key]['sent_ts'])
    y = delays
    x = x[:2000]
    y = y[:2000]
    print(y)
    y -= np.min(y)
    plt.plot(x, y)
    plt.show()


def main():
    path = os.path.join(PROBING_PATH, "probing_2021-03-06-18-17-15.json")
    # path = os.path.join(PROBING_PATH, "probing_2021-03-06-18-24-25.json")
    data = json.load(open(path))
    client_sent = data['clientResult']['sent']
    client_received = data['clientResult']['received']
    server_sent = data['serverResult']['sent']
    server_received = data['serverResult']['received']
    print(f'Uplink packets: {len(client_sent)}, {client_sent[-1]["sequence"] + 1}')
    print(f'Downlink packets: {len(server_sent)}, {server_sent[-1]["sequence"] + 1}')
    print(f'Packet loss ratio, uplink: {"%.2f" % (100 * len(server_received) / len(client_sent))}%, '
          f'downlink {"%.2f" % (100 * len(client_received) / len(server_sent))}%')
    uplink_packets = {}
    for p in client_sent:
        uplink_packets[p['sequence']] = {'sent_ts': p['timestamp']}
    for p in server_received:
        if p['sequence'] in uplink_packets:
            print(p['timestamp'])
            uplink_packets[p['sequence']]['received_ts'] = p['timestamp']
        else:
            print(f'Sequence: {p["sequence"]} not seen in sender')
    analyse(uplink_packets)


if __name__ == '__main__':
    main()
