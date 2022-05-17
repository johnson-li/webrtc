import os
from pprint import pprint
import argparse
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np
from sklearn.linear_model import LinearRegression


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to visualize vehicle locations.')
    parser.add_argument('-p', '--path',
                        default=os.path.expanduser('/tmp/sync'),
                        help='Directory of the clock sync logs')
    args = parser.parse_args()
    return args


def parse_sync_log(path):
    """
        drift = local - remote
    :param path: path of log file
    """
    if os.path.getsize(path) < 1000:
        return {}
    ts = []
    rts = []
    with open(path) as f:
        for line in f.readlines():
            if line.startswith('ts = '):
                line = line[line.index('[') + 1: line.index(']')]
                ts = [int(l) for l in line.split(', ') if l]
            if line.startswith('rts = '):
                line = line[line.index('[') + 1: line.index(']')]
                rts = [int(l) for l in line.split(', ') if l]
    drift_min = -0xffffffffff
    drift_max = 0xffffffffff
    rtt_min = 10000
    timestamp = ts[0]
    for i in range(1, len(ts)):
        rtt = ts[i] - ts[i - 1]
        # if rtt > 10:
        #     continue
        if rtt < rtt_min:
            rtt_min = rtt
        drift = (ts[i] + ts[i - 1]) / 2 - rts[i - 1]
        d_min = drift - rtt / 2
        d_max = drift + rtt / 2
        drift_min = max(drift_min, d_min)
        drift_max = min(drift_max, d_max)
    res = {
        'drift': {
            'range': [drift_min, drift_max],
            'error': (drift_max - drift_min) / 2,
            'value': (drift_max + drift_min) / 2,
            'ts': timestamp
        }
    }
    return res


def regression(drifts):
    drifts = list(filter(lambda x: x, drifts))
    x = [(d['drift']['ts'],) for d in drifts]
    y = [(d['drift']['value'],) for d in drifts]
    model = LinearRegression()
    reg: LinearRegression = model.fit(x, y)
    print(reg.score(x, y))
    x = [(i[0] - np.min(x)) / 1000 / 60 for i in x]
    y = [i[0] - np.min(y) for i in y]
    x = np.array(x)
    y = np.array(y)
    index = np.argsort(x)
    plt.xlabel('Time (minute)')
    plt.ylabel('Clock diff (ms)')
    plt.ylim(0, 50)
    plt.plot(x[index], y[index], 'r,', linewidth=.3)
    plt.savefig('sync.pdf')


def main():
    args = parse_args()
    path = args.path
    if os.path.isdir(path):
        dirs = os.listdir(path)
        drifts = []
        for d in dirs:
            if d.endswith('.sync'):
                ts = d[:-5]
                data = parse_sync_log(os.path.join(path, d), ts)
                if data:
                    drifts.append(data)
        pprint(drifts)
        regression(drifts)
    else:
        data = parse_sync_log(path, 0)
        print(data)


if __name__ == '__main__':
    main()
