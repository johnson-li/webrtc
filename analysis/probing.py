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
PROBING_PATH = os.path.join(RESULTS_PATH, "exp7")


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
    if not res:
        res.append([])
    return np.array(res)


def illustrate_latency(packets, signal_data, title, reg: LinearRegression, draw_signal, xrange, yrange, pkg_size):
    logger.info(f'Illustrating {title}')
    handoff_4g = parse_handoff(signal_data, False)
    handoff_5g = parse_handoff(signal_data, True)
    index_lost = packets[:, 5] == 0

    plt.rcParams['font.family'] = 'sans-serif'
    logger.info(f'[{title}] Packets not received: {np.count_nonzero(packets[:, 5] == 0)}')
    logger.info(f'[{title}] Packets not sent: {np.count_nonzero(packets[:, 6] == 0)}')

    def plot_metrics(ax1, lost, time_range, y_range, metrics):
        ax1.plot(lost, np.ones_like(lost) * np.percentile(y_range, 10), 'xr', ms=2)
        if draw_signal:
            plt.plot(handoff_4g[:, 0], np.ones((handoff_4g.shape[0],)) * np.percentile(y_range, 30), '.g', ms=2)
            plt.plot(handoff_5g[:, 0], np.ones((handoff_5g.shape[0],)) * np.percentile(y_range, 35), '.m', ms=2)
            ts_list = [k for k, v in signal_data.items() if time_range[0] <= k <= time_range[1] and metrics in v]
            ts_list = sorted(ts_list)
            ax2 = ax1.twinx()
            ax2.plot(ts_list, [signal_data[t][metrics] for t in ts_list], 'y.-', linewidth=.4, ms=2)
            ax2.set_ylabel(metrics.upper())
            ax2.yaxis.label.set_color('y')
            ax2.tick_params(axis='y', labelcolor='y')

    def plot_all(figsize=(6, 3), title_prefix='', time_range=None, plot_dot=False, ylim=None, metrics='sinr-nr'):
        # Plot packet transmission latency
        fig = plt.figure(figsize=figsize)
        fig, ax1 = plt.subplots()
        if time_range is None:
            time_range = xrange
        else:
            time_range = [xrange[0] + time_range[0], xrange[0] + time_range[1]]
        index = np.logical_and(np.invert(index_lost),
                               np.logical_and(packets[:, 1] >= time_range[0], packets[:, 1] <= time_range[1]))
        sent = packets[:, 1][index]
        delay = packets[:, 3][index] * 1000
        arrival = packets[:, 2][index]
        lost = packets[:, 1][index_lost]
        y_range = ylim if ylim else [0, np.max(delay) * 1.2]
        ax1.plot(sent, delay, '.-b' if plot_dot else '-b', linewidth=.8, ms=2)
        plot_metrics(ax1, lost, time_range, y_range, metrics)
        ax1.set_xlim(time_range)
        ax1.set_ylim(y_range)
        ax1.set_ylabel('$l_{pkt}$ (ms)')
        ax1.set_xlabel('Sending timestamp (s)')
        ax1.legend(['Packet latency', 'Packet loss', '4G Handoff', '5G Handoff'])
        fig.tight_layout()
        plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'probing_{title_prefix}_{title}.png'), dpi=600,
                    bbox_inches='tight')
        plt.close(fig)
        # Plot throughput
        fig = plt.figure(figsize=figsize)
        fig, ax1 = plt.subplots()
        window_size = .5
        ts_min = xrange[0]
        ts_max = max(xrange[1], yrange[1])
        arrival_data = ((arrival - ts_min) / window_size).astype(int)
        bandwidth_data = np.bincount(arrival_data)
        x = np.arange(bandwidth_data.shape[0]) * window_size + ts_min
        y = bandwidth_data * pkg_size / window_size / 1024 / 1024 * 8
        y_range = [np.min(y) * 0.8, np.max(y) * 1.2]
        ax1.plot(x, y, '.-b' if plot_dot else '-b', linewidth=.8, ms=2)
        plot_metrics(ax1, lost, time_range, y_range, metrics)
        ax1.set_xlim([ts_min, ts_max])
        ax1.set_ylim(y_range)
        ax1.set_ylabel('Bandwidth (Mbps)')
        ax1.set_xlabel('Sending timestamp (s)')
        ax1.legend(['Bandwidth', 'Packet loss', '4G Handoff', '5G Handoff'])
        fig.tight_layout()
        plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'probing_{title_prefix}_bandwidth_{title}.png'), dpi=600,
                    bbox_inches='tight')
        plt.close(fig)
        # Plot packet arrival
        fig = plt.figure(figsize=figsize)
        fig, ax1 = plt.subplots()
        y_range = [np.min(arrival), np.max(arrival)]
        ax1.plot(sent, arrival, '.-b', linewidth=.8, ms=2)
        plot_metrics(ax1, lost, time_range, y_range, metrics)
        ax1.set_xlim(time_range)
        ax1.set_ylim(y_range)
        ax1.set_xlabel('Sending timestamp (s)')
        ax1.set_ylabel('Arrival timestamp (s)')
        ax1.legend(['Packet latency', 'Packet loss', '4G Handoff', '5G Handoff'])
        fig.tight_layout()
        plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'probing_{title_prefix}_arrival_{title}.png'), dpi=600,
                    bbox_inches='tight')
        plt.close(fig)

    plot_all(title_prefix='overall')
    # plot_all(title_prefix='stable', time_range=[20, 21], plot_dot=True)
    # plot_all(figsize=(6, 2), title_prefix='handoff', time_range=[7.5, 8], plot_dot=True)


def illustrate_leading_delay(packets, title):
    arrival = packets[:, 2]
    arrival_pre = np.roll(arrival, 1)
    arrival_pre[0] = 0
    arrival_diff = arrival - arrival_pre
    arrival_continuous = arrival_diff < 0.000005
    leading_index = np.where(np.invert(arrival_continuous))[0]
    leading_index_next = np.roll(leading_index, -1)
    leading_index_next[-1] = arrival.shape[0]
    leading_length = leading_index_next - leading_index
    draw_cdf(leading_length, "Packets in a sending window", f'leading_delay_packets_cdf_{title}.png')
    logger.info(f'[{title}] Number of transaction windows: {leading_index.shape[0]} / {arrival.shape[0]}')
    fig = plt.figure()
    plt.plot(packets[:, 1][leading_index], leading_length)
    # plt.ylim([0, 50])
    plt.xlabel('Sending time (s)')
    plt.ylabel('Packets in a sending window')
    fig.tight_layout()
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'leading_delay_packets_{title}.png'), dpi=600,
                bbox_inches='tight')
    plt.close(fig)


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
    ids = [ids[4]]
    client_sent, client_received, server_sent, server_received = None, None, None, None
    for uid in ids:
        logger.info(f'Parsing {uid}')
        client_path = os.path.join(PROBING_PATH, f"probing_client_{uid}.log")
        server_path = os.path.join(PROBING_PATH, f"server_{uid}.log")
        client_data = json.load(open(client_path))
        server_data = json.load(open(server_path))
        if 'statics' in server_data:
            server_data = server_data['statics']
        client_sent = np.concatenate([client_sent, np.array(client_data['probing_sent'])]) \
            if client_sent is not None else np.array(client_data['probing_sent'])
        client_received = np.concatenate([client_received, np.array(client_data['probing_received'])]) \
            if client_received is not None else np.array(client_data['probing_received'])
        server_sent = np.concatenate([server_sent, np.array(server_data['probing_sent'])]) \
            if server_sent is not None else np.array(server_data['probing_sent'])
        server_received = np.concatenate([server_received, np.array(server_data['probing_received'])]) \
            if server_received is not None else np.array(server_data['probing_received'])
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
            if sender[i][2] > 0:
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
    return {k / 1000: v for k, v in data.items()}


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


def illustrate_location(gps_data, signal_data, nr=False, show=False):
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
    width, height, zoom = 300, 150, 13
    if show:
        width *= 5
        height *= 5
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
    if show:
        fig.show()
    else:
        fig.write_image(os.path.join(RESULT_DIAGRAM_PATH, f'location_{metrics}.pdf'))


def main():
    DRAW_LOCATION = False
    DRAW_LATENCY = True
    DRAW_SIGNAL = True
    reg: LinearRegression = parse_sync(plot=False)
    signal_data = parse_signal_strength() if DRAW_SIGNAL else {}
    if DRAW_LATENCY:
        uplink_packets, downlink_packets = parse_packets(reg)
        pkg_size = uplink_packets[0][4]
        logger.info(f'Packet size: {pkg_size} bytes')
        xrange = (np.min([np.min(uplink_packets[:, 1]), np.min(downlink_packets[:, 1])]),
                  np.max([np.max(uplink_packets[:, 1]), np.max(downlink_packets[:, 1])]))
        yrange = (np.min([np.min(uplink_packets[:, 2]), np.min(downlink_packets[:, 2])]),
                  np.max([np.max(uplink_packets[:, 2]), np.max(downlink_packets[:, 2])]))
        illustrate_latency(uplink_packets, signal_data, 'uplink', reg, DRAW_SIGNAL, xrange, yrange, pkg_size)
        illustrate_latency(downlink_packets, signal_data, 'downlink', reg, DRAW_SIGNAL, xrange, yrange, pkg_size)
        # illustrate_leading_delay(uplink_packets, 'uplink')
        # illustrate_leading_delay(downlink_packets, 'downlink')
        pcis = set([v["pci"] for v in signal_data.values() if "pci" in v])
        nr_pcis = set([v["pci-nr"] for v in signal_data.values() if "pci-nr" in v])
        logger.info(f'Number of PCIs: {len(pcis)}, number of NR-PCIs: {len(nr_pcis)}')
        logger.info(f'PCIs: {pcis}')
        logger.info(f'NR-PCIs: {nr_pcis}')
    if DRAW_LOCATION and DRAW_SIGNAL:
        gps_data = parse_gps()
        illustrate_location(gps_data, signal_data, nr=True, show=True)


if __name__ == '__main__':
    main()
