import os
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np

from analysis.trial import mean_confidence_interval
from analysis.trial.trial import ROUNDS


def main():
    root = os.path.expanduser('~/mobix_trial/mobix/logs/gps')
    data = {}
    i = 0
    for d in sorted(os.listdir(root)):
        ts = datetime.strptime(d[:-4], '%Y-%m-%dT%H:%M:%S.%fZ')
        d = os.path.join(root, d)
        data[ts] = os.path.getsize(d)
    keys = list(sorted(data.keys()))
    ks = [[]]
    for k in keys:
        if k < ROUNDS[i][1]:
            ks[i].append(k)
        else:
            i += 1
            ks.append([])
            ks[i].append(k)
    y = []
    rl = []
    for kk in ks:
        kk_min = np.min(kk)
        kk_max = np.max(kk)
        yy = np.zeros(int((kk_max - kk_min).total_seconds()) + 1)
        rl1 = np.zeros(int((kk_max - kk_min).total_seconds() / 10) + 1)
        rl2 = np.zeros(int((kk_max - kk_min).total_seconds() / 10) + 1)
        for k in kk:
            yy[int((k - kk_min).total_seconds())] += data[k]
            rl2[int((k - kk_min).total_seconds() / 10)] += 1
            if data[k] > 0:
                rl1[int((k - kk_min).total_seconds() / 10)] += 1
        yy = yy * 8
        y.append(yy)
        r = rl1 / rl2 * 100
        r = r[np.logical_not(np.isnan(r))]
        rl.append(r)
    d = []
    for yy in rl:
        for yyy in yy:
            d.append(yyy)
    print("asdfasdf")
    print(np.mean(d))
    print(np.median(d))
    print(np.std(d))
    print(mean_confidence_interval(d))
    print(np.percentile(d, 95))
    plt.boxplot(y)
    plt.xlabel('Rounds')
    plt.ylabel('Data rate (bps)')
    plt.show()
    plt.boxplot(rl)
    plt.xlabel('Rounds')
    plt.ylabel('Reliability (%)')
    plt.show()

    print(len(data))
    dd = []
    for i in y:
        for ii in i:
            dd.append(ii)
    print(np.mean(dd))
    print(np.median(dd))
    print(np.std(dd))
    print(np.max(dd))
    print(np.min(dd))
    print(mean_confidence_interval(dd))
    print(np.percentile(dd, 95))


if __name__ == '__main__':
    main()
