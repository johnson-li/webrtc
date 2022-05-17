import os
from datetime import datetime, timedelta
import numpy as np
from analysis.trial import mean_confidence_interval
from analysis.trial.trial import ROUNDS
import matplotlib.pyplot as plt


def main():
    root = os.path.expanduser('~/mobix_trial')
    data = {}
    success = {}
    for d in os.listdir(root):
        d = os.path.join(root, d)
        for dd in os.listdir(d):
            if dd.endswith('logs'):
                dd = os.path.join(d, dd)
                for ddd in os.listdir(dd):
                    if ddd.endswith('dns.log'):
                        ts = datetime.strptime(ddd.split('.')[0], '%Y-%m-%d-%H-%M-%S') - \
                             timedelta(hours=2, minutes=0)
                        ddd = os.path.join(dd, ddd)
                        suc = False
                        for line in open(ddd).readlines():
                            line = line.strip()
                            if 'Query time: ' in line:
                                lat = int(line[15: -5])
                                data[ts] = lat
                                suc = True
                        success[ts] = suc
    print(len(data))
    y = list(data.values())
    print(f'mean: {np.mean(y)}')
    print(f'median: {np.median(y)}')
    print(np.std(y))
    print(np.max(y))
    print(np.min(y))
    print(np.percentile(y, 95))
    print(mean_confidence_interval(y))

    def draw_success():
        keys = sorted(success.keys())
        i = 0
        ks = [[]]
        for k in keys:
            if k < ROUNDS[i][1]:
                ks[i].append(k)
            else:
                i += 1
                ks.append([])
                ks[i].append(k)
        x = range(1, len(ks) + 1)
        y = []
        for kk in ks:
            yy = []
            for k in kk:
                yy.append(success[k])
            yy = np.array(yy)
            y.append(np.count_nonzero(yy) / len(yy) * 100)
        plt.bar(range(1, len(y) + 1), y)
        plt.xlabel('Round')
        plt.ylabel('Reliability (%)')
        plt.show()
        arr = np.array(list(success.values()))
        sc = np.count_nonzero(arr)
        fc = len(success) - sc
        print(np.mean(y))
        print(np.median(y))
        print(np.std(y))
        print(np.max(y))
        print(np.min(y))
        print(mean_confidence_interval(y))
        print(np.percentile(y, 95))

    def draw():
        keys = sorted(data.keys())
        i = 0
        ks = [[]]
        for k in keys:
            if k < ROUNDS[i][1]:
                ks[i].append(k)
            else:
                i += 1
                ks.append([])
                ks[i].append(k)
        x = range(1, len(ks) + 1)
        y = []
        for kk in ks:
            yy = []
            for k in kk:
                yy.append(data[k])
            y.append(yy)
        plt.boxplot(y)
        plt.xlabel('Round')
        plt.ylabel('RTT (ms)')
        plt.show()

    draw()
    draw_success()


if __name__ == '__main__':
    main()
