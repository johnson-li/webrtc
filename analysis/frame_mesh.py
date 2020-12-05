import argparse
import os
import numpy as np
from multiprocessing import Pool
from analysis.illustrator_mesh import get_meta
from analysis.frame import handle_frame0, load_caches
from analysis.parser import parse_results_accuracy
from analysis.main import get_results_accuracy
import matplotlib.pyplot as plt


def parse_args():
    parser = argparse.ArgumentParser(description='A tool for visualization in a heatmap.')
    parser.add_argument('-p', '--path', default=os.path.expanduser('~/Data/webrtc_exp9'), help='Data directory')
    args = parser.parse_args()
    return args


def normalized(a):
    min_a = min(a)
    max_a = max(a)
    a = np.array(a)
    return (a - min_a) / (max_a - min_a)


def illustrate():
    baseline = {'mAP': [0.4721483103140973, 0.568125532086497],
                'sharpness': [114.10812989191997, 113.98667774570598],
                'contrast': [56.41311732567193, 56.410936394345406]}

    data = [
        {'bitrate': '500', 'mAP': 0.35416431834410544, 'sharpness': 135.11802049755576, 'contrast': 60.672957958698554},
        {'bitrate': '1000', 'mAP': 0.3845808569164617, 'sharpness': 107.40676041912793, 'contrast': 62.20434015843233},
        {'bitrate': '1500', 'mAP': 0.4347775125722245, 'sharpness': 117.27781172301371, 'contrast': 62.45690073785249},
        {'bitrate': '2000', 'mAP': 0.4476506151100408, 'sharpness': 121.98015759544745, 'contrast': 62.67329530233029},
        {'bitrate': '2500', 'mAP': 0.4627952132190798, 'sharpness': 127.8585052824888, 'contrast': 62.59183570376822},
        {'bitrate': '3500', 'mAP': 0.48026399568367983, 'sharpness': 131.4842112015621, 'contrast': 62.613898167703866},
        {'bitrate': '4000', 'mAP': 0.4828407986237899, 'sharpness': 133.09098335784228, 'contrast': 62.743062047715085},
        {'bitrate': '4500', 'mAP': 0.4883549698715618, 'sharpness': 136.87536598897546, 'contrast': 62.784653337932696},
        {'bitrate': '5000', 'mAP': 0.4884877039311074, 'sharpness': 138.5134646421183, 'contrast': 62.74698842695032},
        {'bitrate': '5500', 'mAP': 0.4896621847286934, 'sharpness': 138.05496432276513, 'contrast': 62.753146584356664},
        {'bitrate': '6000', 'mAP': 0.4911457876719653, 'sharpness': 143.23627813378832, 'contrast': 62.66634052236511},
        {'bitrate': '7000', 'mAP': 0.4946909518513012, 'sharpness': 135.08568754290047, 'contrast': 62.85007688664858},
        {'bitrate': '8000', 'mAP': 0.4984503750944156, 'sharpness': 149.10872875409805, 'contrast': 62.7878893326954},
        {'bitrate': '9000', 'mAP': 0.4935750191617705, 'sharpness': 161.111903060731, 'contrast': 63.59850127151203},
        {'bitrate': '10000', 'mAP': 0.3440309557575266, 'sharpness': 163.9495567544371, 'contrast': 63.74681561345141},
    ]
    data2 = [
        {'bitrate': '500', 'mAP': 0.41097143088793425, 'sharpness': 135.11802049755576, 'contrast': 60.672957958698554},
        {'bitrate': '1000', 'mAP': 0.4529023468460017, 'sharpness': 107.40676041912793, 'contrast': 62.20434015843233},
        {'bitrate': '1500', 'mAP': 0.4990079780860308, 'sharpness': 117.27781172301371, 'contrast': 62.45690073785249},
        {'bitrate': '2000', 'mAP': 0.5220124279204329, 'sharpness': 121.98015759544745, 'contrast': 62.67329530233029},
        {'bitrate': '2500', 'mAP': 0.5352253231306388, 'sharpness': 127.8585052824888, 'contrast': 62.59183570376822},
        {'bitrate': '3500', 'mAP': 0.5582912706182154, 'sharpness': 131.4842112015621, 'contrast': 62.613898167703866},
        {'bitrate': '4000', 'mAP': 0.5557262638058522, 'sharpness': 133.09098335784228, 'contrast': 62.743062047715085},
        {'bitrate': '4500', 'mAP': 0.5627039790511466, 'sharpness': 136.87536598897546, 'contrast': 62.784653337932696},
        {'bitrate': '5000', 'mAP': 0.5684053310084918, 'sharpness': 138.5134646421183, 'contrast': 62.74698842695032},
        {'bitrate': '5500', 'mAP': 0.5657150717039094, 'sharpness': 138.05496432276513, 'contrast': 62.753146584356664},
        {'bitrate': '6000', 'mAP': 0.5665039101493182, 'sharpness': 143.23627813378832, 'contrast': 62.66634052236511},
        {'bitrate': '7000', 'mAP': 0.5712444330441206, 'sharpness': 135.08568754290047, 'contrast': 62.85007688664858},
        {'bitrate': '8000', 'mAP': 0.5703264143590562, 'sharpness': 149.10872875409805, 'contrast': 62.7878893326954},
        {'bitrate': '9000', 'mAP': 0.5607400979020415, 'sharpness': 161.111903060731, 'contrast': 63.59850127151203},
        {'bitrate': '10000', 'mAP': 0.5651374350158047, 'sharpness': 163.9495567544371, 'contrast': 63.74681561345141},
    ]
    data = sorted(data, key=lambda x: int(x['bitrate']))
    bitrate = [int(d['bitrate']) for d in data]
    accuracy = [d['mAP'] for d in data]
    # accuracy = normalized(accuracy)
    sharpness = normalized([d['sharpness'] for d in data])
    contrast = normalized([d['contrast'] for d in data])
    plt.figure(figsize=(9, 6))
    plt.plot(bitrate, accuracy)
    plt.plot(bitrate, sharpness)
    plt.plot(bitrate, contrast)
    plt.legend(['Accuracy', 'Sharpness', 'Contrast'])
    plt.xlabel('Bitrate (Kbps)')
    plt.show()


def handle_frames(bitrate, path, weight, caches):
    baseline = path.endswith('baseline')
    dump_dir = path
    if not baseline:
        dump_dir = os.path.join(path, 'dump')
    if baseline:
        indexes = [p.split('.')[0] for p in os.listdir(dump_dir) if p.endswith(f'{weight}.txt')]
        indexes = [int(i) for i in indexes if i.isnumeric()]
        indexes = sorted(indexes)
    else:
        indexes = sorted([int(p.split('.')[0]) for p in os.listdir(dump_dir) if p.endswith('.bin')])
    if len(os.listdir(dump_dir)) < 20:
        return None
    detections = parse_results_accuracy(path, weight=weight)
    accuracy = get_results_accuracy(detections, path, weight=weight)
    mAP = accuracy['mAP']
    sharpness = []
    contrast = []
    for index in indexes:
        res = handle_frame0(path, weight, caches, index, baseline=baseline, accuracy=False)
        sharpness.append(res['sharpness'])
        contrast.append(res['contrast'])
    return {'bitrate': bitrate, 'mAP': mAP, 'sharpness': np.median(sharpness), 'contrast': np.median(contrast)}


def main():
    args = parse_args()
    path = args.path
    records = {}
    for d in os.listdir(path):
        d = os.path.join(path, d)
        meta_path = os.path.join(d, 'metadata.txt')
        if not os.path.isfile(meta_path):
            continue
        meta = get_meta(meta_path)
        records.setdefault(meta['resolution'], {})[meta['bitrate']] = d
    resolution = '1920x1280'
    weight = 'yolov5x'
    caches = load_caches()
    res = handle_frames(0, os.path.expanduser('~/Data/webrtc_exp3/baseline'), weight, caches)
    # with Pool(12) as pool:
    #     res = pool.starmap(handle_frames,
    #                        [(bitrate, path, weight, caches) for bitrate, path in records[resolution].items()])
    print(res)


if __name__ == '__main__':
    main()
    # illustrate()
