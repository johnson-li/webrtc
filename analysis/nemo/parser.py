import argparse
import pprint

import numpy as np
import matplotlib.pyplot as plt
import os
import csv
from utils.base import RESULT_DIAGRAM_PATH


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to parse the csv file exported from NEMO.')
    parser.add_argument('-p', '--path', default=os.path.expanduser('~/Downloads/central_railway_station.csv'),
                        help='Path of the NEMO export file')
    args = parser.parse_args()
    return args


def convert_ts(value):
    if not value:
        return None
    h, m, s = [float(v) for v in value.split(':')]
    return ((h * 60 + m) * 60 + s) * 1000


def parse_csv(path):
    with open(path, newline='') as file:
        data = {}
        names = []
        for row in csv.reader(file):
            if not names:
                names = row
                for n in names:
                    data[n] = []
                continue
            if not row:
                break
            ts = convert_ts(row[0])
            for i, v in enumerate(row):
                if i == 0:
                    continue
                if v:
                    name = names[i]
                    if 'SINR' in name:
                        pass
                    if name in ['SINR (NR serving cell)']:
                        v = float(v.split(', ')[0])
                        data[name].append((ts, v))
                    else:
                        data[name].append((ts, v))
    return data


def illustrate_single(data, title=''):
    x = np.array([v[0] for v in data])
    y = np.array([v[1] for v in data])
    plt.xlabel('Time (ms)')
    plt.ylabel(title)
    plt.plot(x, y)
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'{title.replace(" ", "_")}.pdf'))


def main():
    args = parse_args()
    path = args.path
    data = parse_csv(path)
    key = 'SINR (NR serving cell)'
    illustrate_single(data[key], key)
    a = list(filter(lambda x: 'throughput' in x, data.keys()))
    pprint.pprint(a)


if __name__ == '__main__':
    main()
