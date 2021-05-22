from analysis.probing import parse_sync
from sklearn.linear_model import LinearRegression
from utils.base import RESULT_DIAGRAM_PATH
import numpy as np
from experiment.base import RESULTS_PATH, DATA_PATH
import json
import matplotlib.pyplot as plt
import os

STRESS_PATH = os.path.join(RESULTS_PATH, "stress3")


def main():
    reg: LinearRegression = parse_sync(path=STRESS_PATH, plot=False)
    ids = [f[11:-4] for f in os.listdir(STRESS_PATH) if f.startswith('udp_client_')]
    data = {}
    for i in ids:
        server_log = json.load(open(os.path.join(STRESS_PATH, f'server_{i}.log')))['udp_sink']
        client_log = json.load(open(os.path.join(STRESS_PATH, f'udp_client_{i}.log')))
        data[i] = {'packets': [], 'fps': client_log['fps'], 'bitrate': client_log['bitrate'],
                   'pkg_size': client_log['pkg_size'], 'lost': [], 'count': len(client_log['udp_sink'])}
        for sent_ts, seq, _ in client_log['udp_sink']:
            sent_ts *= 1000
            seq = str(seq)
            if seq in server_log:
                rtt = server_log[seq]['timestamp'] + reg.predict([[sent_ts]])[0] - sent_ts
                data[i]['packets'].append([seq, sent_ts, rtt])
            else:
                data[i]['lost'].append([seq, sent_ts])
    x = [data[i]['bitrate'] for i in ids]
    y = [np.median([p[2] for p in data[i]['packets']]) for i in ids]
    lost = [[len(data[i]['lost']) / data[i]['count'] for i in ids]]
    idx = np.argsort(x)
    x = np.take(x, idx) / 1024 / 1024
    y = np.take(y, idx)
    lost = np.take(lost, idx)
    print(lost)
    plt.xlabel('Sending rate (Mbps)')
    plt.ylabel('Packet transmission latency (ms)')
    plt.plot(x, y)
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'stress_sink.pdf'))


if __name__ == '__main__':
    main()
