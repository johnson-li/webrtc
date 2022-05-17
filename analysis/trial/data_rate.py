import os
import numpy as np
from datetime import datetime, timedelta
from analysis.trial.trial import ROUNDS
from analysis.parser import parse_logger, parse_sender
from analysis.trial import mean_confidence_interval
import matplotlib.pyplot as plt
import re


def main():
    root = os.path.expanduser('~/mobix_trial')
    data = []
    i = 0
    bitrate_list = []
    for d in sorted(os.listdir(root)):
        d = os.path.join(root, d)
        for dd in sorted(os.listdir(d)):
            if dd.endswith('.logs'):
                pkg_size_map = {}
                pkg_send_map = {}
                ts = datetime.strptime(dd.split('.')[0], '%a %b %d %H:%M:%S %Z %Y')
                dd = os.path.join(d, dd)
                client_log = os.path.join(dd, 'client2.log')
                if os.path.exists(client_log):
                    for l in open(client_log).readlines():
                        l = l.strip()
                        if 'OnBitrateUpdated' in l:
                            bitrate = int(re.findall(r', bitrate (\d+)', l)[0])
                            ts = int(re.findall(r'\[(\d+)\]', l)[0])
                            bitrate_list.append((ts, bitrate))

    def print_statics():
        y = np.array([b[1] for b in bitrate_list]) / 1024 / 1024
        print(f'No. of samples: {len(bitrate_list)}')
        print(f'Mean: {np.mean(y)}')
        print(f'Median: {np.median(y)}')
        print(f'Std: {np.std(y)}')
        print(f'Max: {np.max(y)}')
        print(f'Min: {np.min(y)}')
        print(f'5%: {np.percentile(y, 5)}')
        print(f'95%: {np.percentile(y, 95)}')
        print(f'CI: {mean_confidence_interval(y)}')

    def draw_all():
        x = np.array([b[0] for b in bitrate_list])
        y = np.array([b[1] for b in bitrate_list]) / 1024 / 1024
        x -= np.min(x)
        plt.plot(x, y)
        plt.xlabel('Time (ms)')
        plt.ylabel('Bitrate (Mbps)')
        plt.xlim((0, 3e6))
        plt.show()

    def draw_rounds():
        i = 0
        keys = [b[0] for b in bitrate_list]
        bitrate_data = {b[0]: b[1] for b in bitrate_list}
        ks = [[]]
        for k in keys:
            dt = datetime.fromtimestamp(k / 1e3) - timedelta(hours=2, minutes=0)
            if dt < ROUNDS[i][1]:
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
                yy.append(bitrate_data[k] / 1024 / 1024)
            y.append(yy)
        plt.boxplot(y)
        plt.xlabel('Round')
        plt.ylabel('Bitrate (Mbps)')
        plt.show()

    print_statics()
    draw_all()
    draw_rounds()


if __name__ == '__main__':
    main()
