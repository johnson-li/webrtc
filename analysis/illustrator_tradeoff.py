import argparse
import numpy as np
import json
from utils.files import get_meta
from utils.base import RESULT_DIAGRAM_PATH
from utils.plot import init_figure_wide
from analysis.illustrator_mesh import parse_latency
from multiprocessing import Pool
from utils.cache import cache
from utils.const import get_resolution_p
from analysis.parser import parse_inference_latency
from analysis.latency_mesh import load_network_latency
import os
import matplotlib.pyplot as plt


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to visualize latency and accuracy.')
    parser.add_argument('-p', '--path', default=os.path.expanduser('~/Data/webrtc_exp3'), help='Experiment path')
    parser.add_argument('-i', '--inference', default=os.path.expanduser('~/Data/webrtc_exp3_inari/webrtc_exp3'),
                        help='Inference path')
    parser.add_argument('-n', '--network', default=os.path.expanduser('~/Workspace/webrtc-controller/results'),
                        help='Network path')
    args = parser.parse_args()
    return args


def analyse_latency(p, weight, resolution, bitrate):
    latency_path = os.path.join(p, f'dump/stream_local.{weight}.log')
    if not os.path.isfile(latency_path):
        return {}
    latency = parse_inference_latency(latency_path)
    return {'resolution': resolution, 'bitrate': bitrate, 'weight': weight, 'latency': latency}


def load_latency_network():
    result = {}
    data = load_network_latency()
    for d in data:
        if d['category'] == 'No CC':
            result[d['bitrate']] = d['frame_transmission_latency']['med']
    return result


# @cache
def load_latency_inference(path):
    weights = ['yolov5s', 'yolov5x']
    result = {}
    params = []
    for d in os.listdir(path):
        if d == 'latest' or d.startswith('baseline'):
            continue
        d = os.path.join(path, d)
        meta_path = os.path.join(d, 'metadata.txt')
        if not os.path.isfile(meta_path):
            continue
        meta = get_meta(meta_path)
        for w in weights:
            params.append((d, w, meta['resolution'], meta['bitrate']))
    pool = Pool(12)
    res = pool.starmap(analyse_latency, params)
    for r in res:
        if r:
            result.setdefault(get_resolution_p(r['resolution']), {}).setdefault(r['bitrate'], {})[r['weight']] = \
                np.median(r['latency'])
    return result


@cache
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


def analyse_accuracy(path, weight, resolution, bitrate):
    path = os.path.join(path, f'analysis_accuracy.{weight}.json')
    data = json.load(open(path))
    mAP = data['statics']['mAP']
    return {'resolution': resolution, 'bitrate': bitrate, 'mAP': mAP, 'weight': weight}


@cache
def load_accuracy_metrics(path):
    weights = ['yolov5s', 'yolov5x']
    params = []
    result = {}
    for d in os.listdir(path):
        if d == 'latest' or d.startswith('baseline'):
            continue
        d = os.path.join(path, d)
        meta_path = os.path.join(d, 'metadata.txt')
        if not os.path.isfile(meta_path):
            continue
        meta = get_meta(meta_path)
        for w in weights:
            params.append((d, w, meta['resolution'], meta['bitrate']))
    pool = Pool(12)
    res = pool.starmap(analyse_accuracy, params)
    for r in res:
        result.setdefault(get_resolution_p(r['resolution']), {}).setdefault(r['bitrate'], {})[r['weight']] = r['mAP']
    return result


def illustrate(latency, latency_inference, latency_network, accuracy, metrics='all'):
    """
    Supported metrics: codec, inference, network, all, soft
    """
    fig, ax, font_size = init_figure_wide((4.5, 3))
    weights = ['YOLOv5s', 'YOLOv5x'] if metrics in ['inference', 'all', 'soft'] else ['yolov5s']
    tags = ['o', 'x']
    for index, weight in enumerate(weights):
        data = []
        for resolution, v in latency.items():
            for bitrate, vv in v.items():
                lat = 0
                if metrics == 'codec':
                    lat = vv['decoding_latency2'] + vv['encoding_latency']
                elif metrics == 'inference':
                    lat = latency_inference[resolution][bitrate][weight.lower()]
                elif metrics == 'soft':
                    lat = vv['decoding_latency2'] + vv['encoding_latency'] + \
                          latency_inference[resolution][bitrate][weight.lower()]
                elif metrics == 'network':
                    if int(bitrate) % 1000 == 0:
                        lat = latency_network[int(bitrate) / 1000]
                elif metrics == 'all':
                    if int(bitrate) % 1000 == 0:
                        lat = latency_network[int(bitrate) / 1000] + \
                              vv['decoding_latency2'] + vv['encoding_latency'] + \
                              latency_inference[resolution][bitrate][weight.lower()]
                acc = accuracy[resolution][bitrate][weight.lower()]
                if lat:
                    data.append((lat, acc))
        x = [d[0] for d in data]
        y = [d[1] for d in data]
        plt.plot(x, y, tags[index], linewidth=.5)
    if metrics == 'codec':
        plt.xlabel('Latency (encoding + decoding)')
    elif metrics == 'inference':
        plt.xlabel('Latency (inference)')
    elif metrics == 'soft':
        plt.xlabel('Latency (encoding + decoding + inference)')
    elif metrics == 'network':
        plt.xlabel('Latency (frame transmission)')
    elif metrics == 'all':
        plt.xlabel('Latency (overall)')
    if len(weights) > 1:
        plt.legend(weights)
    plt.ylabel('Accuracy')
    plt.tight_layout(pad=.3)
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'tradeoff_{metrics}.pdf'))
    plt.show()


def main():
    args = parse_args()
    path = args.path
    latency_network = load_latency_network()
    latency_metrics = load_latency_metrics(path)
    latency_metrics_inari = load_latency_inference(args.inference)
    accuracy_metrics = load_accuracy_metrics(path)
    illustrate(latency_metrics, latency_metrics_inari, latency_network, accuracy_metrics)


if __name__ == '__main__':
    main()
