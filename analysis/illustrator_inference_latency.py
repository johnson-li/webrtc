import os
import matplotlib
from multiprocessing import Pool
from utils.files import get_meta
from utils.base import RESULT_DIAGRAM_PATH
import matplotlib.pyplot as plt
from analysis.parser import parse_inference_latency
import argparse
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to visualize inference latency.')
    parser.add_argument('-p', '--path', default=os.path.expanduser('~/Data/webrtc_exp3_mobix/webrtc_exp3'),
                        help='Data directory')
    args = parser.parse_args()
    return args


def handle(path, weight):
    meta = get_meta(os.path.join(path, 'metadata.txt'))
    resolution = meta['resolution']
    bitrate = meta['bitrate']
    latency_path = os.path.join(path, f'dump/stream_local.{weight}.log')
    if not os.path.isfile(latency_path):
        return {}
    data = parse_inference_latency(latency_path)
    return {'resolution': resolution, 'bitrate': bitrate, 'latency': np.median(data), 'weight': weight}


def illustrate(data, weights):
    font_size = 16
    fig, ax = plt.subplots(figsize=(4, 2.5))
    for weight in weights:
        res = {}
        for d in data:
            if d and d['weight'] == weight:
                res.setdefault(d['resolution'], []).append(d['latency'])
        res = {k: np.median(v) for k, v in res.items()}
        keys = list(res.keys())
        keys = list(sorted(keys, key=lambda x: float(x.split('x')[0])))
        x = [float(k.split('x')[0]) / 1920 for k in keys]
        y = [res[k] for k in keys]
        plt.plot(x, y, linewidth=2)
    matplotlib.rcParams.update({'font.size': font_size})
    ax.tick_params(axis='both', which='major', labelsize=font_size)
    ax.tick_params(axis='both', which='minor', labelsize=font_size)
    plt.xlabel('Resolution scale', size=font_size)
    plt.ylabel('Latency (ms)', size=font_size)
    plt.legend(weights)
    fig.tight_layout(pad=.3)
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'plot_med_inference_latency.pdf'))


def main():
    weights = ['yolov5s', 'yolov5x']
    args = parse_args()
    path = args.path
    pool = Pool(12)
    params = []
    for d in os.listdir(path):
        if 'baseline' in d:
            continue
        for w in weights:
            params.append((os.path.join(path, d), w))
    data = pool.starmap(handle, params)
    illustrate(data, weights)


if __name__ == '__main__':
    main()
