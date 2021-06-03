import os
import numpy as np
import json
import matplotlib.pyplot as plt
from experiment.base import RESULTS_PATH
from utils.base import RESULT_DIAGRAM_PATH
from analysis.sync import parse_sync_log
import plotly.express as px
from analysis.blackhole import COLORS1, COLORS2, COLORS3, TOKEN
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
import matplotlib as mpl
from utils2.logging import logging
from utils.plot import draw_cdf

mpl.rcParams['agg.path.chunksize'] = 10000
logger = logging.getLogger(__name__)
PROBING_PATH = os.path.join(RESULTS_PATH, "exp6")


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


def illustrate_latency(packets, signal_data, title, reg: LinearRegression):
    logger.info(f'Illustrating {title}')
    handoff_4g = parse_handoff(signal_data, False)
    handoff_5g = parse_handoff(signal_data, True)
    index_lost = packets[:, 5] == 0

    # x, y, z = np.array(x), np.array(delays), np.array(arrivals)
    # index = np.argsort(x)
    # x, y, z = x.take(index), y.take(index), z.take(index)
    # handoff_4g = [h for h in handoff_4g if x[0] <= h[0] <= x[-1]]
    # handoff_5g = [h for h in handoff_5g if x[0] <= h[0] <= x[-1]]
    # trans_data = [np.array(x), np.array(y), np.array(z)]
    # loss_data = [np.array(lost), np.array([15 for _ in lost])]
    # ho_4g_data = [np.array([h[0] for h in handoff_4g]), np.array([25 for _ in handoff_4g])]
    # ho_5g_data = [np.array([h[0] for h in handoff_5g]), np.array([35 for _ in handoff_5g])]
    # ts_offset = np.min(trans_data[0])
    # trans_data[0] = (trans_data[0] - ts_offset)
    # loss_data[0] = (loss_data[0] - ts_offset)
    # ho_4g_data[0] = (ho_4g_data[0] - ts_offset)
    # ho_5g_data[0] = (ho_5g_data[0] - ts_offset)
    # logger.info(
    #     f'[{title}] RTT statics, min: {np.min(y)}, 10%: {np.percentile(y, 10)}, med: {np.median(y)}, avg: {np.average(y)}, '
    #     f'90%: {np.percentile(y, 90)}, 99%: {np.percentile(y, 99)}, max: {np.max(y)}')
    # plt.rcParams['font.family'] = 'sans-serif'

    def plot_all():
        fig = plt.figure(figsize=(6, 3))
        sent = packets[:, 1][np.invert(index_lost)]
        delay = packets[:, 3][np.invert(index_lost)] * 1000
        plt.plot(sent, delay, linewidth=.8)

        lost = packets[:, 1][index_lost]
        plt.plot(lost, np.ones_like(lost) * 20, 'x', ms=4)
        # plt.plot(ho_4g_data[0], ho_4g_data[1], 'o', ms=4)
        # plt.plot(ho_5g_data[0], ho_5g_data[1], 'o', ms=4)
        plt.ylim([0, 200])
        plt.ylabel('$l_{pkt}$ (ms)')
        plt.xlabel('Sending time (s)')
        plt.legend(['Packet latency', 'Packet loss', '4G Handoff', '5G Handoff'])
        fig.tight_layout()
        plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'probing_{title}_overall.png'), dpi=600, bbox_inches='tight')

    def plot_stable():
        plot_range = np.array([2.2, 2.3]) + np.min(packets[:, 1])
        fig = plt.figure(figsize=(6, 2))
        index = np.logical_and(np.invert(index_lost),
                               np.logical_and(packets[:, 1] >= plot_range[0], packets[:, 1] <= plot_range[1]))
        sent = packets[:, 1][index]
        delay = packets[:, 3][index] * 1000
        arrival = packets[:, 2][index]

        plt.plot(sent, delay, '.-', linewidth=.8, ms=4)
        # plt.plot(loss_data[0], loss_data[1], 'x', ms=4)
        # plt.plot(ho_4g_data[0], ho_4g_data[1], 'o', ms=4)
        # plt.plot(ho_5g_data[0], ho_5g_data[1], 'o', ms=4)
        plt.xlim(plot_range)
        plt.ylabel('$l_{pkt}$ (ms)')
        plt.xlabel('Sending time (s)')
        fig.tight_layout()
        plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'probing_stable_{title}.png'), dpi=600, bbox_inches='tight')
        fig = plt.figure(figsize=(6, 2))
        plt.plot(sent, arrival, '.-', linewidth=.8, ms=4)
        plt.ylabel('Arrival timestamp (ms)')
        plt.xlabel('Sending time (s)')
        fig.tight_layout()
        plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'probing_stable_arrival_{title}.png'), dpi=600,
                    bbox_inches='tight')

    def plot_handoff():
        fig = plt.figure(figsize=(6, 2))
        plt.plot(trans_data[0], trans_data[1] * 1000, linewidth=.8, ms=4)
        plt.plot(loss_data[0], loss_data[1], 'x', ms=4)
        plt.plot(ho_4g_data[0], ho_4g_data[1] * 4, 'o', ms=4)
        plt.plot(ho_5g_data[0], ho_5g_data[1] * 4, 'o', ms=4)
        plt.ylim([0, 250])
        plt.xlim([383, 390])
        plt.ylabel('$l_{pkt}$ (ms)')
        plt.xlabel('Sending time (s)')
        plt.legend(['Packet latency', 'Packet loss', '4G Handoff', '5G Handoff'])
        fig.tight_layout()
        plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'probing_handoff_{title}.png'), dpi=600, bbox_inches='tight')

    plot_all()
    plot_stable()
    # plot_handoff()


def illustrate_leading_delay(packets, title):
    packets = list(packets.values())[0]
    seqs = sorted(packets.keys())
    arrival_ts = -1
    leading_ts = -1
    leading_delay = []
    for seq in seqs:
        packet = packets[seq]
        if 'received_ts' not in packet:
            continue
        sent_ts, received_ts = packet['sent_ts'], packet['received_ts']
        if arrival_ts == -1:
            leading_ts = sent_ts
            arrival_ts = received_ts
        else:
            if received_ts - arrival_ts < 0.0005:
                continue
            else:
                leading_delay.append(sent_ts - leading_ts)
                leading_ts = sent_ts
                arrival_ts = received_ts
    # fig = plt.figure()
    # plt.plot()
    # plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'leading_delay_{title}.png'), dpi=600)
    leading_delay = np.array(leading_delay) * 1000
    draw_cdf(leading_delay, "Time (ms)", f'leading_delay_cdf_{title}.png')


def convert(records, uid, client=False):
    if 'timestamp' not in records[0]:
        return [{'timestamp': r[0], 'sequence': r[1], 'uid': uid, 'lost': r[2] < 0, 'size': r[2]} for r in records]
    return [{**r, 'uid': uid} for r in records]


def parse_packets(reg: LinearRegression):
    ids = []
    for f in os.listdir(PROBING_PATH):
        if f.startswith('probing_'):
            ids.append(f.split('.')[0].split('_')[-1])
    ids = sorted(ids)
    ids = [ids[0]]
    client_sent, client_received, server_sent, server_received = None, None, None, None
    for uid in ids:
        client_path = os.path.join(PROBING_PATH, f"probing_client_{uid}.log")
        server_path = os.path.join(PROBING_PATH, f"server_{uid}.log")
        client_data = json.load(open(client_path))
        server_data = json.load(open(server_path))
        if 'statics' in server_data:
            server_data = server_data['statics']
        client_sent = np.concatenate([client_sent, np.array(client_data['probing_sent'])]) \
            if client_sent else np.array(client_data['probing_sent'])
        client_received = np.concatenate([client_received, np.array(client_data['probing_received'])]) \
            if client_received else np.array(client_data['probing_received'])
        server_sent = np.concatenate([server_sent, np.array(server_data['probing_sent'])]) \
            if server_sent else np.array(server_data['probing_sent'])
        server_received = np.concatenate([server_received, np.array(server_data['probing_received'])]) \
            if server_received else np.array(server_data['probing_received'])
    seq_uplink_max = int(np.max(client_sent[:, 1]))
    seq_downlink_max = int(np.max(server_sent[:, 1]))
    logger.info(f'Uplink packets (sent), num: {len(client_sent)}, max seq: {seq_uplink_max}')
    logger.info(f'Downlink packets (sent), num: {len(server_sent)}, max seq: {seq_downlink_max}')
    logger.info(f'Packet loss ratio, uplink: {"%.2f" % (100 * (1 - len(server_received) / len(client_sent)))}%, '
                f'downlink {"%.2f" % (100 * (1 - len(client_received) / len(server_sent)))}%')

    # Format: seq, sent_ts, received_ts, delay, size, received, sent
    uplink_packets = np.zeros((seq_uplink_max + 1, 7))
    downlink_packets = np.zeros((seq_downlink_max + 1, 7))

    def feed(sender, receiver, result: np.ndarray, reg: LinearRegression, client_as_sender=False):
        size = result.shape[0]
        result[:, 0] = np.arange(0, size)
        index = np.argsort(sender[:, 1])
        result[:, 4] = sender[index, 2]
        for i in range(sender.shape[0]):
            result[int(sender[i][1]), 1] = sender[i][0]
            result[int(sender[i][1]), 6] = 1
        for i in range(receiver.shape[0]):
            result[int(receiver[i][1]), 2] = receiver[i][0]
            result[int(receiver[i][1]), 5] = 1
        if client_as_sender:
            result[:, 2] = reg.predict(np.expand_dims(result[:, 2], axis=1))
        else:
            result[:, 1] = reg.predict(np.expand_dims(result[:, 1], axis=1))
        result[:, 3] = result[:, 2] - result[:, 1]

    feed(client_sent, server_received, uplink_packets, reg, True)
    feed(server_sent, client_received, downlink_packets, reg, False)
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


def parse_sync(path=PROBING_PATH, plot=False):
    log_path = os.path.join(path, 'sync')
    fake = not os.path.exists(log_path)
    if not fake:
        files = [os.path.join(log_path, f) for f in os.listdir(log_path) if f.endswith('sync')]
        syncs = []
        for f in files:
            sync_log = parse_sync_log(f)
            if not sync_log:
                continue
            sync = parse_sync_log(f)['drift']
            if sync['error'] < 15:
                syncs.append(sync)
        x = np.array([s['ts'] for s in syncs]) / 1000
        y = np.array([s['ts'] - s['value'] for s in syncs]) / 1000
        y = np.expand_dims(y, axis=1)
    else:
        y = np.array([[1], [2]])
        x = np.array([1, 2])
    reg = LinearRegression().fit(y, x)
    pred = reg.predict(y)
    mse = mean_squared_error(pred, x)
    if plot:
        plt.plot(x.squeeze(), y.squeeze(), 'x')
        plt.title('Sync')
        plt.show()
    if not fake:
        logger.info(f'Clock sync, confidence: {np.mean([s["error"] for s in syncs])}, mean square error: {mse}')
    return reg


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
    data = []
    for ts, d in signal_data.items():
        gps = find_location(gps_data, ts)
        i = {'lat': gps['lat'], 'lon': gps['lon']}
        if 'pci' in d:
            sinr = d['sinr']
            i.update({'PCI': str(d['pci']), 'RSSI': d['rssi'], 'SINR': sinr, 'RSRP': d['rsrp'], 'RSRQ': d['rsrq']})
        if 'pci-nr' in d:
            sinr_nr = d['sinr-nr']
            if sinr_nr < -100 or sinr_nr > 60:
                sinr_nr = 0
            i.update({'PCI-NR': str(d['pci-nr']), 'RSRP-NR': d['rsrp-nr'], 'RSRQ-NR': d['rsrq-nr'], 'SINR-NR': sinr_nr})
        data.append(i)
    metrics = 'SINR-NR'
    data = list(filter(lambda x: metrics in x and 'lat' in x and 'lon' in x, data))
    hover_data = ['lat', 'lon', 'PCI', 'RSSI', 'SINR', 'RSRP', 'RSRQ', 'PCI-NR', 'RSRP-NR', 'RSRQ-NR', 'SINR-NR']
    hover_data = ['PCI', 'PCI-NR', 'SINR', 'SINR-NR']
    center = {'lat': np.mean([np.max([d['lat'] for d in data]), np.min([d['lat'] for d in data])]),
              'lon': np.mean([np.max([d['lon'] for d in data]), np.min([d['lon'] for d in data])])}
    height = 150
    width = 300
    zoom = 13
    if 'PCI' in metrics:
        values = list(set([str(d[metrics]) for d in data]))
        fig = px.scatter_mapbox(data, lat='lat', lon='lon', color_discrete_map=dict(zip(values, COLORS3[:len(values)])),
                                center=center, color=metrics, zoom=zoom, hover_data=hover_data, width=width,
                                height=height)
    else:
        fig = px.scatter_mapbox(data, lat='lat', lon='lon', color=metrics, hover_data=hover_data,
                                center=center, zoom=zoom, width=width, height=height)
    fig.update_layout(mapbox={'accesstoken': TOKEN, 'style': 'mapbox://styles/johnsonli/cknwxq6o92sj017o5ivdph021'})
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    fig.write_image(os.path.join(RESULT_DIAGRAM_PATH, f'location_{metrics}.pdf'))


def main():
    DRAW_LOCATION = True
    DRAW_LATENCY = True
    DRAW_SIGNAL = True
    reg: LinearRegression = parse_sync(plot=False)
    signal_data = parse_signal_strength() if DRAW_SIGNAL else {}
    if DRAW_LATENCY:
        uplink_packets, downlink_packets = parse_packets(reg)
        logger.info(f'Packet size: {uplink_packets[0][4]} bytes')
        illustrate_latency(uplink_packets, signal_data, 'uplink', reg)
        illustrate_latency(downlink_packets, signal_data, 'downlink', reg)
        # illustrate_leading_delay(uplink_packets, 'uplink')
        # illustrate_leading_delay(downlink_packets, 'downlink')
        pcis = set([v["pci"] for v in signal_data.values() if "pci" in v])
        nr_pcis = set([v["pci-nr"] for v in signal_data.values() if "pci-nr" in v])
        logger.info(f'Number of PCIs: {len(pcis)}, number of NR-PCIs: {len(nr_pcis)}')
        logger.info(f'PCIs: {pcis}')
        logger.info(f'NR-PCIs: {nr_pcis}')
    if DRAW_LOCATION:
        gps_data = parse_gps()
        illustrate_location(gps_data, signal_data)


if __name__ == '__main__':
    main()
