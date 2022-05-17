import os
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt


def main():
    root = os.path.expanduser('~/mobix_trial')
    data = {}
    count = 0
    log_ts = np.array([], dtype=int)
    for d in os.listdir(root):
        d = os.path.join(root, d)
        ts_list = []
        for dd in os.listdir(d):
            if dd.endswith('.logs'):
                count += 1
                ts = datetime.strptime(dd[:-5], '%a %b %d %H:%M:%S %Z %Y')
                dd = os.path.join(d, dd)
                ts_list.append(ts)
        ts_list = np.array(sorted([t.timestamp() for t in ts_list]), dtype=int)
        duration_list = ts_list[1:] - ts_list[: -1]
        # log_ts += duration_list
    # x = np.range(0, 200, step=10)
    # y = np.zeros_like(x)

    # for i in range(x.shape[0]):
    #     y[i] =
    print(f'Count: {count}')

    def draw():
        x = range(1, 13)
        y = [100 for i in x]
        plt.xlabel('Round')
        plt.ylabel('Handover success rate (%)')
        plt.bar(x, y)
        plt.show()

    draw()


if __name__ == '__main__':
    main()
