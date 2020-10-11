import os
import json
import gmplot
from experiment.base import RESULTS_PATH
import numpy as np

BLACKHOLE_PATH = os.path.join(RESULTS_PATH, "blackhole/demo1")
PCIS = {}
COLORS1 = ['#488f31', '#6da046', '#8eb15d', '#adc276', '#cad491', '#e6e6ae', '#fffacc', '#f6dfa8', '#f1c388', '#eca56e',
           '#e6865c', '#df6453', '#de425b']
COLORS2 = ['#003f5c', '#2f4b7c', '#665191', '#a05195', '#d45087', '#f95d6a', '#ff7c43', '#ffa600']


def parse(filename):
    with open(filename) as f:
        data = []
        for line in f.readlines():
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def handle(data):
    for d in data:
        cellular_info = d['cellularInfo']['cellInfoList']
        print(cellular_info[0])


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
        print(records)
        latency_list = [r['remoteTimestamp'] - r['localTimestamp'] + -1825722090 for r in records if
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


def read_measurement():
    locations = []
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
                        cell_info = list(filter(lambda x: x['isRegistered'], cell_info_list))[0]
                        identity = cell_info['identity']
                        signal_strength = cell_info['signalStrength']
                        pci = identity.get('pci', '')
                        if 'rsrp' not in signal_strength:
                            continue
                        rsrp, rsrq, rssi = signal_strength['rsrp'], signal_strength['rsrq'], signal_strength['rssi']
                        if pci:
                            PCIS[pci] = PCIS.get(pci, 0) + 1
                        locations.append({'latitude': location['latitude'], 'longitude': location['longitude'],
                                          'time': location['time'], 'pci': pci, 'rsrp': rsrp, 'rsrq': rsrq,
                                          'rssi': rssi})
    return locations


def get_color(value, min_value, max_value):
    gray = int(0xff * (max_value - value) / (max_value - min_value))
    return f'#{gray:02x}{gray:02x}{gray:02x}'


def illustrate(locations):
    apikey = 'AIzaSyB5jY90h8QE8UbM5UQXxg5h-VaT2DAzdIw'
    gmap = gmplot.GoogleMapPlotter(60.169292, 24.941905, 16, apikey=apikey)
    locations = sorted(locations, key=lambda x: x['time'])

    def draw_base_stations():
        print(f"PCIS: {PCIS}")
        keys = list(PCIS.keys())
        colors = COLORS1
        for i in range(min(len(colors), len(PCIS))):
            pci = keys[i]
            locations_pci = filter(lambda x: x['pci'] == pci, locations)
            locations_pci = [(loc['latitude'], loc['longitude']) for loc in locations_pci]
            lats, lngs = zip(*locations_pci)
            gmap.scatter(lats, lngs, color=colors[i], size=4, marker=False)

    def draw_signal_strength():
        metrics = 'rsrq'
        values = sorted(list(set([loc[metrics] for loc in locations])))
        min_value, max_value = min(values), max(values)
        print(f'Min {metrics}: {min_value}, max {metrics}: {max_value}')
        colors = \
            [(loc['latitude'], loc['longitude'], get_color(loc[metrics], min_value, max_value)) for loc in locations]
        color_candidates = sorted(list(set([c[2] for c in colors])))
        for color in color_candidates:
            locations_color = filter(lambda x: x[2] == color, colors)
            locations_color = [loc[:2] for loc in locations_color]
            lats, lngs = zip(*locations_color)
            gmap.scatter(lats, lngs, color=color, size=4, marker=False)

    def draw_pour():
        pass

    def draw_sink():
        pass

    # draw_base_stations()
    draw_signal_strength()
    # draw_sink()

    gmap.draw('map.html')


def main():
    # read_pour()
    locations = read_measurement()
    # pours, sinks = read_pour(), read_sink()
    illustrate(locations)


if __name__ == '__main__':
    main()
