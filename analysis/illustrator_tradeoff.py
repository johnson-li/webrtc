import argparse
from analysis.illustrator_mesh import parse_latency
from multiprocessing import Pool
from utils.cache import cache
from utils.const import get_resolution_p, get_resolutions0
from analysis.accuracy_mesh import work
import os


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to visualize latency and accuracy.')
    parser.add_argument('-p', '--path', default=os.path.expanduser('~/Data/webrtc_exp3'), help='Experiment path')
    args = parser.parse_args()
    return args


def load_latency_metrics(path):
    pool = Pool(12)
    metrics = ['decoding_latency2', 'encoding_latency', 'frame_transmission_latency', ]
    res = pool.starmap_async(parse_latency, [(path, m) for m in metrics])
    res = res.get()
    result = {}
    for m, r in zip(metrics, res):
        for resolution, v in r.items():
            for bitrate, value in v.items():
                result.setdefault(get_resolution_p(resolution), {}).setdefault(bitrate, {})[m] = value[0]
    return result


def load_accuracy_metrics(path):
    weights = ['yolov5s', 'yolov5x']
    res = []
    for w in weights:
        r = work(path, w, [], get_resolutions0())
        res.append(r)
    return res


def main():
    args = parse_args()
    path = args.path
    # latency_metrics = load_latency_metrics(path)
    # print(latency_metrics)
    accuracy_metrics = load_accuracy_metrics(path)
    print(accuracy_metrics)


if __name__ == '__main__':
    main()
