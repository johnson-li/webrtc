import os
import json
import matplotlib.pyplot as plt
from experiment.base import RESULTS_PATH
import plotly.express as px
import numpy as np

BLACKHOLE_PATH = os.path.join(RESULTS_PATH, "blackhole/demo1")
PCIS = {}
COLORS1 = ['#488f31', '#6da046', '#8eb15d', '#adc276', '#cad491', '#e6e6ae', '#fffacc', '#f6dfa8', '#f1c388', '#eca56e',
           '#e6865c', '#df6453', '#de425b']
COLORS2 = ['#003f5c', '#2f4b7c', '#665191', '#a05195', '#d45087', '#f95d6a', '#ff7c43', '#ffa600']
COLORS3 = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe',
           '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000', '#aaffc3', '#808000', '#ffd8b1', '#000075', '#808080',
           '#ffffff', '#000000']
TOKEN = 'pk.eyJ1Ijoiam9obnNvbmxpIiwiYSI6ImNpbnRvNGwwbTExOG51a2x5NXV0YjlvN2kifQ.5h1a1DNB2VZVf-SdS12TEQ'
BIAS = -2312718480


def parse(filename):
    with open(filename) as f:
        data = []
        for line in f.readlines():
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def read_pour():
    for f in os.listdir(BLACKHOLE_PATH):
        if f.startswith('udp_pour'):
            f = os.path.join(BLACKHOLE_PATH, f)
            for line in open(f).readlines():
                line = line.strip()
                if line:
                    line = json.loads(line)
                    return


def read_sink():
    def parse_data(records):
        bandwidth_list = {}
        bandwidth_measure_period = 1000
        records = sorted(records, key=lambda x: x['localTimestamp'])
        start_ts = min([r.get('remoteTimestamp', 0xffffff) for r in records])
        latency_list = [r['remoteTimestamp'] - r['localTimestamp'] + BIAS for r in records if
                        'remoteTimestamp' in r]
        packet_loss = len(list(filter(lambda x: 'remoteTimestamp' not in x, records))) / len(records)
        print(latency_list)
        for record in records:
            if 'remoteTimestamp' in record:
                bucket = int((record['remoteTimestamp'] - start_ts) / bandwidth_measure_period)
                bandwidth_list[bucket] = bandwidth_list.get(bucket, 0) + record['size']
        bandwidth_list = {(k, v * 1000 / bandwidth_measure_period) for k, v in bandwidth_list.items()}
        print(bandwidth_list)
        # print(f'Packet loss: {packet_loss * 100:.2f}%')
        return packet_loss, latency_list, bandwidth_list

    for f in sorted(os.listdir(BLACKHOLE_PATH)):
        if f.startswith('udp_sink') and f not in ['udp_sink_2020-10-05-20-15-44.json']:
            f = os.path.join(BLACKHOLE_PATH, f)
            data = json.load(open(f))
            parse_data(data)
            return


def convert_dict(val):
    ans = {}
    for i in val:
        k = i['key']
        v = i['value']
        t = i['valueType']
        if t == 'java.lang.Boolean':
            v = bool(v)
        elif t in ['java.lang.Long', 'java.lang.Integer']:
            v = int(v)
        elif t in ['java.lang.Float']:
            v = float(v)
        ans[k] = v
    return ans


def analyse_reports(prefs, packets):
    period = 500
    res = {}
    if prefs[0] == 'sink':
        bitrate = prefs[3] / 1024 / 1024
        if prefs[1] == 'UDP':
            packets = sorted(packets, key=lambda x: x['localTimestamp'])
            start_ts, end_ts = packets[0]['localTimestamp'], packets[-1]['localTimestamp']
            for p in packets:
                if 'remoteTimestamp' not in p:
                    continue
                index = int((p['localTimestamp'] - start_ts) / period)
                res.setdefault(index, {'ts': start_ts + index * period + period / 2, 'min_seq': 0xfffff, 'max_seq': -1,
                                       'data_size': 0, 'delay_list': []})
                res[index]['min_seq'] = min(res[index]['min_seq'], p['sequence'])
                res[index]['max_seq'] = max(res[index]['max_seq'], p['sequence'])
                res[index]['delay_list'].append(p['remoteTimestamp'] - p['localTimestamp'] + BIAS)
                res[index]['data_size'] += p['size']
        elif prefs[1] == 'TCP':
            packets = sorted(packets, key=lambda x: x['localTimestamp'])
            start_ts, end_ts = packets[0]['localTimestamp'], packets[-1]['localTimestamp']
            for p in packets:
                index = int((p['localTimestamp'] - start_ts) / period)
                res.setdefault(index, {'ts': start_ts + index * period + period / 2, 'data_size': 0})
                res[index]['data_size'] += p['size']
    elif prefs[0] == 'pour':
        bitrate = prefs[4] / 1024 / 1024
        if prefs[2] == 'UDP':
            packets = sorted(packets, key=lambda x: x['localTs'])
            print(packets[0].keys())
            print(packets[0]['localTs'])
            start_ts, end_ts = packets[0]['localTs'], packets[-1]['localTs']
            for p in packets:
                # if 'localTs' not in p or 'remoteTs' not in p:
                #     continue
                index = int((p['localTs'] - start_ts) / period)
                res.setdefault(index, {'ts': start_ts + index * period + period / 2, 'min_seq': 0xfffff, 'max_seq': -1,
                                       'data_size': 0, 'delay_list': []})
                res[index]['min_seq'] = min(res[index]['min_seq'], p['seq'])
                res[index]['max_seq'] = max(res[index]['max_seq'], p['seq'])
                res[index]['delay_list'].append(p['localTs'] - p['remoteTs'] - BIAS)
                res[index]['data_size'] += p['size']
        elif prefs[2] == 'TCP':
            pass
    return res


def read_measurement():
    locations = []
    bitrates = {}
    sync = []
    for f in os.listdir(BLACKHOLE_PATH):
        if f.startswith('measurement'):
            f = os.path.join(BLACKHOLE_PATH, f)
            for line in open(f).readlines():
                line = line.strip()
                if line:
                    line = json.loads(line)
                    cell_info_list, date_time, timestamp, location = \
                        line['cellInfoList'], line['dateTime'], line['timeStamp'], line.get('location', None)
                    if cell_info_list and date_time and timestamp and location:
                        for cell_info in cell_info_list:
                            identity = cell_info['identity']
                            registered = cell_info['isRegistered']
                            signal_strength = cell_info['signalStrength']
                            pci = identity.get('pci', '')
                            if 'rsrp' not in signal_strength:
                                continue
                            rsrp, rsrq, rssi = signal_strength['rsrp'], signal_strength['rsrq'], signal_strength['rssi']
                            if pci:
                                PCIS[pci] = PCIS.get(pci, 0) + 1
                            locations.append({'latitude': location['latitude'], 'longitude': location['longitude'],
                                              'time': location['time'], 'localTime': location['localTime'], 'pci': pci,
                                              'rsrp': rsrp, 'rsrq': rsrq, 'rssi': rssi, 'registered': registered})
        elif f.startswith('udp_') or f.startswith('tcp_'):
            f = os.path.join(BLACKHOLE_PATH, f)
            data = json.load(open(f))
            prefs = convert_dict(data['preferenceReports'])
            prefs = 'sink' if 'sink' in f else 'pour', prefs['sink mode'], prefs['pour mode'], prefs['sink bitrate'], \
                    prefs['pour bitrate']
            reports = data['packetReports']
            bitrates.setdefault(prefs, [])
            bitrates[prefs].append(analyse_reports(prefs, reports))
        elif f.startswith('sync_'):
            f = os.path.join(BLACKHOLE_PATH, f)
            data = json.load(open(f))
            sync.append((data['clockDrift'], data['confidence'], data['localTs'][0]))
    return locations, bitrates, sync


def get_color(value, min_value, max_value):
    gray = int(0xff * (max_value - value) / (max_value - min_value))
    return f'#{gray:02x}{gray:02x}{gray:02x}'


def illustrate(locations, bitrates, sync):
    locations = sorted(locations, key=lambda x: x['time'])
    pcis = sorted(PCIS, key=PCIS.get, reverse=True)
    print(f'Number of locations: {len(locations)}')
    print(f"PCIs (len: {len(PCIS)}): {PCIS}")

    # Parameters
    # locations = locations[:40000]
    start_ts = locations[0]['localTime']
    end_ts = locations[-1]['localTime']
    print(f'Period: [{start_ts} - {end_ts}]')
    locations = list(filter(lambda x: x['registered'], locations))
    metrics = ['rssi', 'rsrp', 'rsrq'][1]
    colors = COLORS3
    # pci = pcis[0]
    pci = None

    if pci:
        locations = list(filter(lambda x: x['pci'] == pci, locations))

    def draw_base_stations():
        fig = px.scatter_mapbox(locations, lat='latitude', lon='longitude', hover_data=['pci'],
                                color='pci', color_discrete_map=dict(zip(pcis, colors[:len(pcis)])), zoom=16)
        fig.update_layout(mapbox_style="basic", mapbox_accesstoken=TOKEN)
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        fig.show()

    def draw_signal_strength():
        fig = px.scatter_mapbox(locations, lat='latitude', lon='longitude', hover_data=['pci', metrics], color=metrics,
                                zoom=16)
        fig.update_layout(mapbox_style="basic", mapbox_accesstoken=TOKEN)
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        fig.show()

    def draw_pour():
        pass

    def draw_sink():
        for k, v in bitrates.items():
            data = []
            for t in v:
                for i, p in t.items():
                    delay_list = p.pop('delay_list')
                    p['delay_avg'] = np.mean(delay_list)
                    p['packet_loss'] = 1 - len(delay_list) / (p['max_seq'] - p['min_seq'] + 1)
                    data.append(p)
            if k[0] == 'sink':
                bitrate = k[3] / 1024 / 1024
                data = sorted(data, key=lambda x: x['ts'])
                start_ts = data[0]['ts']

                # Plot transmission delay
                plt.plot([(d['ts'] - start_ts) / 1000 for d in data], [d['delay_avg'] for d in data])
                plt.ylim(0, 100)
                plt.xlabel('Time (s)')
                plt.ylabel('Transmission Delay (ms)')
                plt.title(f'Sink, bitrate: {bitrate} Mbps')
                plt.show()

                # Plot throughput
                plt.plot([(d['ts'] - start_ts) / 1000 for d in data],
                         [d['data_size'] * 1000 / 500 * 8 / 1024 / 1024 for d in data])
                plt.ylim(0, bitrate * 1.2)
                plt.xlabel('Time (s)')
                plt.ylabel('Throughput (Mbps)')
                plt.title(f'Sink, bitrate: {bitrate} Mbps')
                plt.show()

                # Plot packet loss
                plt.plot([(d['ts'] - start_ts) / 1000 for d in data],
                         [d['packet_loss'] * 100 for d in data])
                plt.xlabel('Time (s)')
                plt.ylabel('Packet loss ratio (%)')
                plt.title(f'Sink, bitrate: {bitrate} Mbps')
                plt.show()

            elif k[0] == 'pour':
                bitrate = k[4] / 1024 / 1024
                data = sorted(data, key=lambda x: x['ts'])
                protocol = k[2]
                start_ts = 0

                if protocol == 'UDP':
                    # Plot transmission delay
                    plt.plot([(d['ts'] - start_ts) / 1000 for d in data], [d['delay_avg'] for d in data])
                    plt.ylim(0, 100)
                    plt.xlabel('Time (s)')
                    plt.ylabel('Transmission Delay (ms)')
                    plt.title(f'Pour, bitrate: {bitrate} Mbps')
                    plt.show()
                else:
                    print(k)
                    print(data)

                # Plot throughput
                plt.plot([(d['ts'] - start_ts) / 1000 for d in data],
                         [d['data_size'] * 1000 / 500 * 8 / 1024 / 1024 for d in data])
                plt.xlabel('Time (s)')
                plt.ylabel('Throughput (Mbps)')
                plt.ylim(0, bitrate * 1.2)
                plt.title(f'Pour, bitrate: {bitrate} Mbps')
                plt.show()

                # Plot packet loss
                plt.plot([(d['ts'] - start_ts) / 1000 for d in data],
                         [d['packet_loss'] * 100 for d in data])
                plt.xlabel('Time (s)')
                plt.ylabel('Packet loss ratio (%)')
                plt.title(f'Pour, bitrate: {bitrate} Mbps')
                plt.show()

    # draw_base_stations()
    draw_signal_strength()
    # draw_sink()


def main():
    # read_pour()
    locations, bitrates, sync = read_measurement()
    # pours, sinks = read_pour(), read_sink()
    illustrate(locations, bitrates, sync)


if __name__ == '__main__':
    main()
