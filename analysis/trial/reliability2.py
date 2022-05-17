import os
from datetime import datetime

import matplotlib.pyplot as plt

from analysis.trial.trial import ROUNDS


def main():
    root = os.path.expanduser('~/mobix_trial/mobix/logs/gps')
    data_recv = {}
    data_send = {}
    i = 0
    for d in sorted(os.listdir(root)):
        ts = datetime.strptime(d[:-4], '%Y-%m-%dT%H:%M:%S.%fZ')
        d = os.path.join(root, d)
        data_recv[ts] = os.path.getsize(d)
    for root in [os.path.expanduser('~/mobix_trial/webrtc'), os.path.expanduser('~/mobix_trial/webrtc2')]:
        for dd in sorted(os.listdir(root)):
            if dd.endswith('.logs'):
                dd = os.path.join(root, dd)
                dd = os.path.join(dd, 'gps')
                if os.path.isdir(dd):
                    for f in os.listdir(dd):
                        if f.endswith('.json'):
                            ts = datetime.strptime(f[:-5], '%Y-%m-%dT%H:%M:%S.%fZ')
                            data_send[ts] = 1

    data_recv = {k: v for k, v in data_recv.items() if v > 0}
    keys = list(sorted(data_send.keys()))
    keys_lost = list(sorted({k: v for k, v in data_send.items() if k not in data_recv}.keys()))
    print(len(keys))
    print(len(keys_lost))
    ks = [[]]
    ks_loss = [[]]
    i = 0
    for k in keys:
        if k < ROUNDS[i][1]:
            ks[i].append(k)
        else:
            i += 1
            ks.append([])
            ks[i].append(k)
    i = 0
    for k in keys_lost:
        if k < ROUNDS[i][1]:
            ks_loss[i].append(k)
        else:
            i += 1
            ks_loss.append([])
            ks_loss[i].append(k)
    print([len(i) for i in ks])
    print([len(i) for i in ks_loss])
    keys = sorted(data_recv.keys())
    print(len(keys))
    plt.plot(keys[:2000], '.')
    plt.xlabel('Data index')
    plt.ylabel('Data reception time')
    plt.show()
    plt.plot(keys[7000:], '.')
    plt.xlabel('Data index')
    plt.ylabel('Data reception time')
    plt.show()


if __name__ == '__main__':
    main()
