import os
import json
import numpy as np
from multiprocessing import Pool
import matplotlib.pyplot as plt
from utils.base import RESULT_DIAGRAM_PATH
from utils.plot import init_figure_wide


def handle(path, is_sink, is_fps, bitrate):
    data = {}
    client_log = json.load(open(os.path.join(path, 'udp_client.log')))
    server_log = json.load(open(os.path.join(path, 'udp_server.log')))
    drift = -1729737250 if is_sink else 1729737250
    key = 'udp_sink' if is_sink else 'udp_pour'
    client_log = client_log[key]
    for log in client_log:
        data.setdefault(log[1], {})['sending' if is_sink else 'receiving'] = log[0] * 1000
    server_log = server_log[key]
    for k, v in server_log.items():
        k = int(k)
        data.setdefault(k, {})['receiving' if is_sink else 'sending'] = v['timestamp']
    total = len(data)
    lost = len(list(filter(lambda x: 'receiving' not in x, data.values())))
    delays = [d['receiving'] - d['sending'] + drift for d in data.values() if 'sending' in d and 'receiving' in d]
    reorder_count = 0
    receiving_pre = 0
    for k in sorted(data.keys()):
        d = data[k]
        if not receiving_pre and 'receiving' in d:
            receiving_pre = d['receiving']
        if receiving_pre and 'receiving' in d:
            if d['receiving'] < receiving_pre:
                reorder_count += 1
            receiving_pre = d['receiving']
    statics = {'packet_loss': lost / total, 'min': np.min(delays), 'median': np.median(delays), 'packets': total,
               'top90': np.percentile(delays, 90), 'std': np.std(delays), 'reorder': reorder_count / total}
    return {
        'bitrate': bitrate,
        'statics': statics,
        'sink': is_sink,
        'fps': is_fps,
    }


def ping_statics():
    path = os.path.expanduser('~/Workspace/webrtc-controller/results/ping')
    path = os.path.join(path, 'ping_usb2.log')
    data = []
    for line in open(path).readlines():
        line = line.strip()
        if line.startswith('64 bytes from lab6'):
            rtt = float(line.split(' ')[7].split('=')[-1])
            data.append(rtt)
    data = np.array(data)
    data /= 2
    print(f'Ping statics, min: {np.min(data)}, median: {np.median(data)}, '
          f'top90: {np.percentile(data, 90)}, std: {np.std(data)}')


def illustrate(data):
    res_sink_fps = []
    res_sink = []
    res_pour_fps = []
    res_pour = []
    for d in data:
        if d['sink'] and d['fps']:
            res_sink_fps.append((d['bitrate'], d['statics']))
        if d['sink'] and not d['fps']:
            res_sink.append((d['bitrate'], d['statics']))
        if not d['sink'] and d['fps']:
            res_pour_fps.append((d['bitrate'], d['statics']))
        if not d['sink'] and not d['fps']:
            res_pour.append((d['bitrate'], d['statics']))

    def res_sort(res):
        return sorted(res, key=lambda x: x[0])

    res_sink = res_sort(res_sink)
    res_sink_fps = res_sort(res_sink_fps)
    res_pour = res_sort(res_pour)
    res_pour_fps = res_sort(res_pour_fps)
    x = [r[0] for r in res_sink]
    y_sink = [r[1]['packet_loss'] * 100 for r in res_sink]
    y_sink_fps = [r[1]['packet_loss'] * 100 for r in res_sink_fps]

    fig, ax = init_figure_wide()
    ax.set_xlabel('Bit rate (Mbps)', fontsize='medium', fontweight='normal')
    ax.set_ylabel('Packet loss ratio (%)', fontsize='medium', fontweight='normal')
    plt.plot(x, y_sink, y_sink_fps, linewidth=8)
    plt.ylim((-0.2, 6.5))
    plt.legend(['Average pacing control', 'Burst pacing control'], loc='upper right')
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, "packet_loss.eps"))
    plt.show()

    for r in res_sink_fps:
        print(r[0], '&', "%.1f" % r[1]['min'], '&', "%.1f" % r[1]['median'], '&', "%.1f" % r[1]['top90'], '&',
              "%.1f" % r[1]['std'])


def main():
    ping_statics()
    path = os.path.expanduser('~/Workspace/webrtc-controller/results/congestion_control')
    dirs = os.listdir(path)
    dirs = list(filter(lambda x: x.startswith('pour') or x.startswith('sink'), dirs))
    params = [(os.path.join(path, d), d.startswith('sink'), 'fps' in d, int(d.split('_')[-1][:-1])) for d in dirs]
    pool = Pool(10)
    data = pool.starmap(handle, params)
    illustrate(data)


if __name__ == '__main__':
    main()
