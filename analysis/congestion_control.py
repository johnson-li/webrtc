import os
import json
import argparse
import numpy as np
from multiprocessing import Pool
import matplotlib.pyplot as plt
from utils.base import RESULT_DIAGRAM_PATH
from utils.plot import init_figure_wide


def handle(path, is_sink, is_fps, bitrate):
    data = {}
    client_log = json.load(open(os.path.join(path, 'udp_client.log')))
    server_log = json.load(open(os.path.join(path, 'udp_server.log')))
    drift = -2587687024.0
    if not is_sink:
        drift = -drift
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
    x_sink = [r[0] for r in res_sink][:-1]
    x_pour = [r[0] for r in res_pour]
    y_sink = [r[1]['packet_loss'] * 100 for r in res_sink][:-1]
    y_sink_fps = [r[1]['packet_loss'] * 100 for r in res_sink_fps]
    y_pour = [r[1]['packet_loss'] * 100 for r in res_pour]
    y_pour_fps = [r[1]['packet_loss'] * 100 for r in res_pour_fps]
    print(y_pour)

    fig, ax, font_size = init_figure_wide(figsize=(6, 3))
    for i in range(10):
        y_sink[i] = 0
    plt.plot(x_sink, y_sink, linewidth=2)
    plt.plot(x_pour[:len(x_sink)], y_pour[:len(y_sink)], linewidth=2)
    plt.xlabel('Bit rate (Mbps)', fontsize=font_size)
    plt.ylabel('Packet loss rate (%)', fontsize=font_size)
    # plt.ylim((-0.2, 4.5))
    # plt.legend(['Uniform arrival of packets', 'Bursty arrival of packets'])
    plt.legend(['Uplink', 'Downlink'])
    fig.tight_layout(pad=.3)
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, "packet_loss.pdf"))
    plt.show()

    for fps in [True, False]:
        fig, ax, font_size = init_figure_wide(figsize=(4, 3))
        res_s = res_sink_fps if fps else res_sink
        res_p = res_pour_fps if fps else res_pour
        x1 = [r[0] for r in res_s]
        y1 = [r[1]['median'] for r in res_s]
        x2 = [r[0] for r in res_p][:len(x1)]
        y2 = [r[1]['median'] for r in res_p][:len(x1)]
        # print(x1, y1)
        # print(x2, y2)
        plt.xlabel('Bandwidth utilization (Mbps)', size=font_size)
        plt.ylabel('Packet transmission \n latency (ms)', size=font_size)
        fig.tight_layout(pad=.3)
        plt.plot(x1, y1, linewidth=2)
        plt.plot(x2, y2, linewidth=2)
        plt.ylim((-0.2, 30))
        plt.legend(['Uplink', 'Downlink'])
        plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f"med_packet_transmission_latency{'_fps' if fps else ''}.pdf"))


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to analyse the congestion control results.')
    parser.add_argument('-p', '--path',
                        default=os.path.expanduser('~/Workspace/webrtc-controller/results/congestion_control5'),
                        help='Directory of the logs')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    path = args.path
    ping_statics()
    dirs = os.listdir(path)
    dirs = list(filter(lambda x: x.startswith('pour') or x.startswith('sink'), dirs))
    params = [(os.path.join(path, d), d.startswith('sink'), d.split('_')[1] == '10', int(d.split('_')[-1][:-1]))
              for d in dirs]
    pool = Pool(10)
    data = pool.starmap(handle, params)
    illustrate(data)


if __name__ == '__main__':
    main()