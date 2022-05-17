import re
from datetime import datetime, timedelta
from analysis.trial import mean_confidence_interval
import matplotlib.pyplot as plt
import numpy as np
from analysis.trial.trial import ROUNDS


def get_obu_data():
    f = '/home/johnson/Downloads/logs/usb1_2021-12-10_09_30_57_263187.log'
    data = {}
    duration = {}
    for l in open(f).readlines():
        l = l.strip()
        res = re.findall(r'([0-9\-_]+) (usb\d) \d+ ((True)|(False))', l)
        if res:
            res = res[0]
            ts = datetime.strptime(res[0], '%Y-%m-%d_%H_%M_%S_%f')
            usb = res[1]
            in_use = res[2] == 'True'
            data[ts] = [usb, in_use]
    pre_k = None
    keys = sorted(data.keys())
    for i, k in enumerate(keys):
        if pre_k is None:
            pre_k = k
            duration[pre_k] = ['usb1' if data[k][1] else 'usb2']
        else:
            if data[k][1] != data[pre_k][1]:
                duration[pre_k].append((keys[i - 1] - pre_k).seconds)
                pre_k = k
                duration[pre_k] = ['usb1' if data[k][1] else 'usb2']
    return data, duration


def main():
    data, duration = get_obu_data()
    keys = sorted(data.keys())
    def print_all():
        x = keys
        y = [1 if data[k][1] else 2 for k in keys]
        plt.plot(x, y)
        plt.xlabel('Time')
        plt.ylabel('PLMN')
        plt.show()

    def print_duration():
        x = sorted(duration.keys())
        x = [xx for xx in x if len(duration[xx]) > 1]
        y = [duration[xx][1] for xx in x]
        x = range(len(x))
        plt.plot(x, y)
        plt.xlabel('Time')
        plt.ylabel('Duration (s)')
        plt.show()

    def print_rounds():
        i = 0
        keys = sorted(duration.keys())
        keys = [xx for xx in keys if len(duration[xx]) > 1]
        ks = [[]]
        for k in keys:
            dt = k - timedelta(hours=2, minutes=0)
            if dt < ROUNDS[i][1]:
                ks[i].append(k)
            else:
                while dt >= ROUNDS[i][1]:
                    i += 1
                    ks.append([])
                ks[i].append(k)
        ks = [k for k in ks if k]
        print(ks)
        x = np.array(range(len(ks))) + 3
        y = [[duration[k][1] for k in keys] for keys in ks]
        # plt.plot(x, y)
        plt.boxplot(y)
        plt.xticks(range(1, len(x) + 1), x)
        plt.xlabel('Round')
        plt.ylabel('PLMN continuity time (s)')
        plt.show()

    def print_statics():
        keys = sorted(duration.keys())
        keys = [xx for xx in keys if len(duration[xx]) > 1]
        values = [duration[k][1] for k in keys]
        print(f'Data size: {len(keys)}')
        print(f'mean: {np.mean(values)}')
        print(f'median: {np.median(values)}')
        print(f'std: {np.std(values)}')
        print(f'max: {np.max(values)}')
        print(f'min: {np.min(values)}')
        print(f'5th: {np.percentile(values, 5)}')
        print(f'95th: {np.percentile(values, 95)}')
        print(f'CI: {mean_confidence_interval(values)}')

    print_all()
    print_duration()
    print_rounds()
    print_statics()


if __name__ == '__main__':
    main()
