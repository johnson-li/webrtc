import os
import re
from datetime import datetime, timedelta
from analysis.trial import mean_confidence_interval
import matplotlib.pyplot as plt
import numpy as np

from analysis.trial.trial import ROUNDS


def main():
    root = os.path.expanduser('~/mobix_trial')
    data = {}
    for d in sorted(os.listdir(root)):
        d = os.path.join(root, d)
        for dd in sorted(os.listdir(d)):
            if dd.endswith('.logs'):
                start_ts = None
                end_ts = None
                pkg_size_map = {}
                pkg_send_map = {}
                ts = datetime.strptime(dd.split('.')[0], '%a %b %d %H:%M:%S %Z %Y')
                ts -= timedelta(hours=2, minutes=0)
                dd = os.path.join(d, dd)
                client_log = os.path.join(dd, 'client2.log')
                if os.path.exists(client_log):
                    for l in open(client_log).readlines():
                        l = l.strip()
                        if 'SendPacketToNetwork' in l:
                            tss = int(re.findall(r'Timestamp: (\d+)', l)[0])
                            if not start_ts:
                                start_ts = tss
                            else:
                                end_ts = tss
                data[ts] = (start_ts, end_ts)

    def draw_rounds():
        i = 0
        keys = sorted([k for k in data.keys() if data[k][0] and data[k][1]])
        print(keys)
        ks = [[]]
        for k in keys:
            if k < ROUNDS[i][1]:
                ks[i].append(k)
            else:
                i += 1
                ks.append([])
                ks[i].append(k)
        x = range(len(ks))
        y = [np.sum([data[k][1] - data[k][0] for k in kss]) / (data[kss[-1]][1] - data[kss[0]][0]) for kss in ks]
        plt.bar(x, y)
        plt.xlabel('Rounds')
        plt.ylabel('Reliability')
        plt.show()
        print(len(keys))
        print(max(y))
        print(min(y))
        print(np.mean(y))
        print(np.std(y))
        print(np.median(y))
        print(np.percentile(y, 5))
        print(np.percentile(y, 95))
        print(mean_confidence_interval(y))

    draw_rounds()


def main2():
    root = os.path.expanduser('~/mobix_trial')
    data = {}
    sync_count = {}
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
                        count = 0
                        with open(sync_file) as f:
                            for line in f.readlines():
                                line = line.strip()
                                if line.startswith('Current progress'):
                                    count += 1
                        data[ts] = count
                        sync_count[ts] = count / 20 * 100
    keys = sorted(data.keys())

    def statistics():
        print(f'Count: {len(data)}')

    def print_rounds2():
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
                yy.append(sync_count[k])
            y.append([yyy for yyy in yy])
        # y = [np.sum(yy) / len(yy) / 20 * 100 for yy in y]
        # plt.bar(x, y)
        plt.boxplot(y)
        plt.xlabel('Round')
        plt.ylabel('Reliability (%)')
        plt.ylim((0, 100))
        plt.show()
        # print(f'Mean: {np.mean(y)}')
        # print(f'Mean: {np.median(y)}')
        # print(f'Mean: {np.std(y)}')
        # print(f'Mean: {np.max(y)}')
        # print(f'Mean: {np.min(y)}')
        # print(f'Mean: {np.percentile(y, 95)}')
        # print(f'Mean: {mean_confidence_interval(y)}')

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
                yy.append(data[k])
            y.append([yyy for yyy in yy])
        y = [np.sum(yy) / len(yy) / 20 * 100 for yy in y]
        plt.bar(x, y)
        plt.xlabel('Round')
        plt.ylabel('Reliability (%)')
        plt.ylim((0, 100))
        plt.show()
        print(f'Mean: {np.mean(y)}')
        print(f'Mean: {np.median(y)}')
        print(f'Mean: {np.std(y)}')
        print(f'Mean: {np.max(y)}')
        print(f'Mean: {np.min(y)}')
        print(f'Mean: {np.percentile(y, 95)}')
        print(f'Mean: {mean_confidence_interval(y)}')

    print_rounds()
    print_rounds2()
    statistics()


if __name__ == '__main__':
    # main()
    main2()
