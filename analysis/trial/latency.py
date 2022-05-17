from datetime import datetime, timedelta
import numpy as np
import re
import os
from matplotlib import pyplot as plt

from analysis.trial.trial import ROUNDS
from analysis.trial import mean_confidence_interval


def main():
    root = os.path.expanduser('~/mobix_trial')
    data = {}
    for d in os.listdir(root):
        d = os.path.join(root, d)
        for dd in os.listdir(d):
            if dd.endswith('.logs'):
                dd = os.path.join(d, dd)
                dd = os.path.join(dd, 'sync')
                if os.path.exists(dd):
                    for sync_file in os.listdir(dd):
                        ts = datetime.strptime(sync_file.split('.')[0], '%Y-%m-%d-%H-%M-%S') - \
                             timedelta(hours=2, minutes=0)
                        sync_file = os.path.join(dd, sync_file)
                        ts_list = []
                        with open(sync_file) as f:
                            for line in f.readlines():
                                line = line.strip()
                                if line.startswith('ts = '):
                                    groups = re.findall(re.compile(r'\d+'), line)
                                    ts_list += [int(g) for g in groups]
                                    break
                        if ts_list:
                            data[ts] = np.array(ts_list)
    # print(data)
    rtt_data = {k: v[1:] - v[: -1] for k, v in data.items()}
    keys = sorted(list(rtt_data.keys()))

    def print_time():
        x = np.array([k.timestamp() for k in keys])
        y1 = np.array([np.percentile(rtt_data[k], 10) for k in keys])
        y2 = np.array([np.percentile(rtt_data[k], 50) for k in keys])
        y3 = np.array([np.percentile(rtt_data[k], 90) for k in keys])
        y = np.vstack(rtt_data.values()).reshape(-1)
        plt.figure()
        plt.plot(x[y1 > 8], y1[y1 > 8])
        plt.plot(x[y2 > 8], y2[y2 > 8])
        plt.plot(x[y3 > 8], y3[y3 > 8])
        plt.xlabel('Time (s)')
        plt.ylim((0, 200))
        plt.ylabel('RTT (ms)')
        plt.legend(['10th percentile', '50th percentile', '90th percentile'])
        # plt.xlim((0, 3000))
        # plt.xlim((68000, 74000))
        plt.show()
        y = y[y > 8]
        print(y.shape)
        print(np.mean(y))
        print(np.median(y))
        print(np.std(y))
        print(np.min(y[y > 10]))
        print(np.max(y))
        print(np.percentile(y, 95))
        print(np.percentile(y, 5))
        print(mean_confidence_interval(y))

    def print_rounds():
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
                yy += rtt_data[k].tolist()
            y.append([yyy for yyy in yy if yyy >= 11])
        plt.boxplot(y)
        plt.xlabel('Round')
        plt.ylabel('RTT (ms)')
        plt.ylim((0, 500))
        plt.show()

    print_time()
    print_rounds()


if __name__ == '__main__':
    main()
