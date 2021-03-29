import os
import numpy as np
import matplotlib.pyplot as plt


def parse(line: str, prefix: str):
    res = {}
    if line.startswith(prefix):
        line = line[line.find(']') + 2:]
        d = [l.split(': ') for l in line.split(', ')]
        for dd in d:
            val = dd[1]
            if val.isdigit():
                val = int(val)
            res[dd[0]] = val
    return res


def illustrate(data, xlable='Time (ms)', ylable=''):
    x = np.array([d[0] for d in data])
    y = np.array([d[1] for d in data])
    x -= np.min(x)
    plt.plot(x, y)
    plt.xlabel(xlable)
    plt.ylabel(ylable)
    plt.show()


def main():
    path = os.path.expanduser('~/Data/webrtc_exp4/latest/client2.log')
    target_rate = []
    pacing_rate = []
    for line in open(path).readlines():
        line = line.strip()
        d = parse(line, '(goog_cc_network_control.cc:616)')
        if d:
            target_rate.append((d['time'], d['loss based target rate']))
        d = parse(line, '(goog_cc_network_control.cc:705)')
        if d:
            pacing_rate.append((d['at time'], d['Pacing rate (kbps)']))

    illustrate(target_rate, ylable='Measured target rate (kbps)')
    illustrate(pacing_rate, ylable='Pacing rate (kbps)')


if __name__ == '__main__':
    main()
