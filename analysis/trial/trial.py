import os
import json
from datetime import datetime
import plotly.express as px
from analysis.sync import parse_sync_log

TOKEN = 'pk.eyJ1Ijoiam9obnNvbmxpIiwiYSI6ImNpbnRvNGwwbTExOG51a2x5NXV0YjlvN2kifQ.5h1a1DNB2VZVf-SdS12TEQ'

ROUNDS = [
    (datetime(2021, 12, 9, 12, 44, 5), datetime(2021, 12, 9, 13, 2, 46)),
    (datetime(2021, 12, 9, 13, 2, 47), datetime(2021, 12, 9, 13, 18, 10)),
    (datetime(2021, 12, 9, 13, 18, 11), datetime(2021, 12, 9, 23, 59, 59)),
    (datetime(2021, 12, 10, 1, 1, 1), datetime(2021, 12, 10, 7, 48, 49)),
    (datetime(2021, 12, 10, 7, 48, 49), datetime(2021, 12, 10, 7, 58, 57)),
    (datetime(2021, 12, 10, 7, 58, 57), datetime(2021, 12, 10, 8, 15, 33)),
    (datetime(2021, 12, 10, 8, 15, 33), datetime(2021, 12, 10, 8, 23, 52)),
    (datetime(2021, 12, 10, 8, 23, 52), datetime(2021, 12, 10, 8, 31, 32)),
    (datetime(2021, 12, 10, 8, 31, 32), datetime(2021, 12, 10, 8, 40, 9)),
    (datetime(2021, 12, 10, 8, 40, 9), datetime(2021, 12, 10, 8, 50, 17)),
    (datetime(2021, 12, 10, 8, 50, 17), datetime(2021, 12, 10, 8, 58, 45)),
    (datetime(2021, 12, 10, 8, 58, 45), datetime(2021, 12, 10, 23, 59, 59)),
]


def draw_locations(gps_dataset, round_trip=None):
    data = []
    print(len(gps_dataset.keys()))
    for ts in sorted(gps_dataset.keys()):
        if round_trip is not None:
            if ROUNDS[round_trip][0] <= ts <= ROUNDS[round_trip][1]:
                data.append({'ts': ts, 'lat': gps_dataset[ts]['lat'], 'lon': gps_dataset[ts]['lon']})
        else:
            data.append({'ts': ts, 'lat': gps_dataset[ts]['lat'], 'lon': gps_dataset[ts]['lon']})
    print(data[0])
    print(data[-1])
    fig = px.scatter_mapbox(data, lat='lat', lon='lon', hover_data=['ts'], zoom=15)
    fig.update_layout(mapbox_accesstoken=TOKEN)
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    fig.show()


def main():
    gps_dataset = {}
    drift_dataset = {'lab4': {}, 'lab6': {}}
    root = os.path.expanduser('~/mobix_trial')
    for exp_root in os.listdir(root):
        exp_root = os.path.join(root, exp_root)
        for log_root in os.listdir(exp_root):
            log_root = os.path.join(exp_root, log_root)
            gps_root = os.path.join(log_root, 'gps')
            if os.path.isdir(gps_root):
                for gps_file in os.listdir(gps_root):
                    gps_file = os.path.join(gps_root, gps_file)
                    if gps_file.endswith('.json'):
                        gps_data = json.load(open(gps_file))
                        gps_dataset[datetime.strptime(gps_data['time'], '%Y-%m-%dT%H:%M:%S.%fZ')] = \
                            {'lat': gps_data['lat'], 'lon': gps_data['lon']}
            sync_root = os.path.join(log_root, 'sync')
            if os.path.isdir(sync_root):
                for sync_file in os.listdir(sync_root):
                    ts = datetime.strptime(sync_file.split('.')[0], '%Y-%m-%d-%H-%M-%S')
                    host = sync_file.split('.')[1]
                    sync_file = os.path.join(sync_root, sync_file)
                    drift = parse_sync_log(sync_file)
                    if drift:
                        drift_dataset[host][ts] = drift
    draw_locations(gps_dataset, round_trip=10)
    # print(drift_dataset)


if __name__ == '__main__':
    main()
