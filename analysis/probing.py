import os
import numpy as np
import json
import matplotlib.pyplot as plt
from experiment.base import RESULTS_PATH, DATA_PATH
from utils.base import RESULT_DIAGRAM_PATH
import plotly.express as px
from analysis.blackhole import COLORS3, TOKEN

PROBING_PATH = os.path.join(RESULTS_PATH, "probing2")


# PROBING_PATH = '/tmp/webrtc/logs'


def parse_handoff(signal_data, nr=True):
    pci_key = 'pci-nr' if nr else 'pci'
    res = []
    for ts, signal in signal_data.items():
        if pci_key not in signal:
            continue
        pci = signal[pci_key]
        if not res or pci != res[-1][1]:
            res.append((ts, pci))
    return res


def illustrate_latency(packets, signal_data, title):
    client_send = title == 'uplink'
    ts_key = 'sent_ts' if client_send else 'received_ts'
    handoff_4g = parse_handoff(signal_data, False)
    handoff_5g = parse_handoff(signal_data, True)
    print(f'4G Handoff: {handoff_4g}')
    print(f'5G Handoff: {handoff_5g}')
    keys = packets.keys()
    keys = sorted(list(keys))
    delays = []
    lost = []
    lost_seq = []
    x = []
    for key in keys:
        index = key
        while 'received_ts' not in packets[index]:
            index -= 1
        if 'received_ts' in packets[key]:
            x.append(packets[key][ts_key])
            delays.append(packets[key]['received_ts'] - packets[key]['sent_ts'])
        else:
            lost_seq.append(key)
            lost.append([packets[index][ts_key], 10])

    y = delays
    y -= np.min(y)
    print(f'Packet loss timestamps: {[int(k[0]) for k in lost]}')
    print(f'Packet loss seqs: {lost_seq}')
    handoff_4g = [h for h in handoff_4g if x[0] <= h[0] <= x[-1]]
    handoff_5g = [h for h in handoff_5g if x[0] <= h[0] <= x[-1]]
    plt.plot(x, y)
    plt.plot([l[0] for l in lost], [40 for l in lost], 'x')
    plt.plot([h[0] for h in handoff_4g], [50 for h in handoff_4g], 'o')
    plt.plot([h[0] for h in handoff_5g], [55 for h in handoff_5g], 'o')
    plt.ylabel('Packet Transmission Latency (ms)')
    plt.xlabel('Time (ms)')
    plt.ylim([0, 100])
    plt.legend(['Packet latency', 'Packet loss', '4G Handoff', '5G Handoff'])
    plt.title(title)
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'probing_{title}.png'), dpi=600)
    plt.show()


def convert(records):
    return [{'timestamp': r[0] * 1000, 'sequence': r[1]} for r in records]


def parse_packets():
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
    return uplink_packets, downlink_packets


def parse_gps():
    log_path = os.path.join(PROBING_PATH, 'gps')
    files = os.listdir(log_path)
    timestamps = list(sorted([f[:-5].split('_')[1] for f in files]))
    data = {}
    for ts in timestamps:
        ts = int(ts)
        path = os.path.join(log_path, f'gps_{ts}.json')
        gps_data = json.load(open(path))
        data[ts] = {'ts': gps_data['ts'], 'lat': gps_data['lat'], 'lon': gps_data['lon']}
    return data


def parse_signal_strength():
    log_path = os.path.join(PROBING_PATH, 'quectel')
    files = os.listdir(log_path)
    timestamps = list(sorted([f[:-4].split('_')[1] for f in files]))
    data = {}
    for ts in timestamps:
        if ts == 'server':
            continue
        ts = int(ts)
        path = os.path.join(log_path, f'quectel_{ts}.log')
        data[ts] = {}
        for line in open(path).readlines():
            line = line.strip()
            if line.startswith('+QENG: "LTE"'):
                d = line.split(' ')[1].split(',')
                cellID, pci, tac, rsrp, rsrq, rssi, sinr = \
                    d[4], int(d[5]), d[10], int(d[11]), int(d[12]), int(d[13]), int(d[14])
                data[ts].update({'pci': pci, 'rsrp': rsrp, 'rsrq': rsrq, 'rssi': rssi, 'sinr': sinr})
            if line.startswith('+QENG:"NR5G-NSA"'):
                d = line.split(':')[1].split(',')
                pci, rsrp, sinr, rsrq = int(d[3]), int(d[4]), int(d[5]), int(d[6])
                data[ts].update({'pci-nr': pci, 'rsrp-nr': rsrp, 'sinr-nr': sinr, 'rsrq-nr': rsrq})
    return data


def find_location(gps_data, ts):
    keys = list(gps_data.keys())
    index = np.argmin(np.abs(np.array(keys) - ts))
    gps = gps_data[keys[index]]
    return gps


def find_signal(quectel_data, ts, key='pci-nr'):
    keys = list(quectel_data.keys())
    index = np.argmin(np.abs(np.array(keys) - ts))
    signal = quectel_data[keys[index]]
    return signal


def illustrate_location(gps_data, signal_data, nr=False):
    pci_key = 'pci' if not nr else 'pci-nr'
    pcis = set([v["pci"] for v in signal_data.values() if pci_key in v])
    data = []
    for ts, d in signal_data.items():
        gps = find_location(gps_data, ts)
        i = {'lat': gps['lat'], 'lon': gps['lon']}
        if 'pci' in d:
            i.update({'pci': d['pci'], 'rssi': d['rssi'], 'sinr': d['sinr'], 'rsrp': d['rsrp'], 'rsrq': d['rsrq']})
        if 'pci-nr' in d:
            i.update({'pci-nr': d['pci-nr'], 'rsrp-nr': d['rsrp-nr'], 'rsrq-nr': d['rsrq-nr'], 'sinr-nr': d['sinr-nr']})
        data.append(i)
    metrics = 'rsrq'
    data = filter(lambda x: metrics in x, data)
    fig = px.scatter_mapbox(data, lat='lat', lon='lon', hover_data=['lat', 'lon', 'pci', 'rssi', 'sinr', 'rsrp', 'rsrq',
                                                                    'pci-nr', 'rsrp-nr', 'rsrq-nr', 'sinr-nr'],
                            color=metrics, color_discrete_map=dict(zip(pcis, COLORS3[:len(pcis)])), zoom=16)
    fig.update_layout(mapbox_style="basic", mapbox_accesstoken=TOKEN)
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    fig.show()


def main():
    signal_data = parse_signal_strength()
    gps_data = parse_gps()
    uplink_packets, downlink_packets = parse_packets()
    illustrate_latency(uplink_packets, signal_data, 'uplink')
    illustrate_latency(downlink_packets, signal_data, 'downlink')
    print(f'Number of PCIs: {len(set([v["pci"] for v in signal_data.values() if "pci" in v]))}, '
          f'number of NR-PCIs: {len(set([v["pci-nr"] for v in signal_data.values() if "pci-nr" in v]))}')
    print(f'PCIs: {set([v["pci"] for v in signal_data.values() if "pci" in v])}')
    print(f'NR-PCIs: {set([v["pci-nr"] for v in signal_data.values() if "pci-nr" in v])}')
    # illustrate_location(gps_data, signal_data)


if __name__ == '__main__':
    main()
