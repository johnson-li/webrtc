import os
import re
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np

from analysis.trial import mean_confidence_interval
from analysis.trial.obu_log import get_obu_data
from analysis.trial.trial import ROUNDS


def main():
    root = os.path.expanduser('~/mobix_trial')
    data = []
    data2 = {}
    for d in sorted(os.listdir(root)):
        d = os.path.join(root, d)
        for dd in sorted(os.listdir(d)):
            if dd.endswith('.logs'):
                start_ts = None
                end_ts = None
                pkg_size_map = {}
                pkg_send_map = {}
                ts = datetime.strptime(dd.split('.')[0][:-9], '%a %b %d %H:%M:%S')
                ts = ts.replace(year=2021)
                ts -= timedelta(hours=2, minutes=0)
                dd = os.path.join(d, dd)
                client_log = os.path.join(dd, 'client2.log')
                if os.path.exists(client_log):
                    for l in open(client_log).readlines():
                        l = l.strip()
                        if 'SendPacketToNetwork' in l:
                            tss = int(re.findall(r'Timestamp: (\d+)', l)[0])
                            data.append(tss)
                            if ts not in data2:
                                data2[ts] = [tss, -1]
                            else:
                                data2[ts][1] = tss
    data_obu, duration = get_obu_data()
    duration_keys = sorted(duration.keys())
    # print(sorted(duration.keys()))
    print(duration_keys[0].timestamp())
    plt.plot(data)
    # plt.plot([], [0 for i in range(len(duration_keys))], 'rx')
    plt.xlabel('Data index')
    plt.ylabel('Data reception time')
    # plt.xlim([0, 1e6])
    plt.show()
    keys = sorted(data2.keys())
    data3 = {}
    for i in range(1, len(keys)):
        data3[keys[i]] = (data2[keys[i]][0] - data2[keys[i - 1]][1]) / 1000
    ks = [[]]
    i = 0
    keys = sorted(data3.keys())
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
            yy.append(data3[k])
        y.append([yyy for yyy in yy])
    plt.boxplot(y)
    plt.xlabel('Round')
    plt.ylabel('Service interruption time')
    plt.ylim((0, 60))
    plt.show()
    data3 = np.array(list(data3.values()))
    data3 = data3[data3 < 200]
    print(data3.shape)
    print(np.mean(data3))
    print(np.median(data3))
    print(np.std(data3))
    print(np.max(data3))
    print(np.min(data3))
    print(mean_confidence_interval(data3))
    print(np.percentile(data3, 95))


if __name__ == '__main__':
    main()
