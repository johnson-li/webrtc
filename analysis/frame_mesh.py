import argparse
import os
import numpy as np
from multiprocessing import Pool
from analysis.illustrator_mesh import get_meta
from analysis.frame import handle_frame0, load_caches
from analysis.parser import parse_results_accuracy
from analysis.main import get_results_accuracy


def parse_args():
    parser = argparse.ArgumentParser(description='A tool for visualization in a heatmap.')
    parser.add_argument('-p', '--path', default=os.path.expanduser('~/Data/webrtc_exp9'), help='Data directory')
    args = parser.parse_args()
    return args


def handle_frames(bitrate, path, weight, caches):
    indexes = sorted([int(p.split('.')[0]) for p in os.listdir(os.path.join(path, 'dump')) if p.endswith('.bin')])
    dump_dir = os.path.join(path, 'dump')
    if (len(os.listdir(dump_dir)) < 20):
        return None
    detections = parse_results_accuracy(path, weight=weight)
    accuracy = get_results_accuracy(detections, path, weight=weight)
    mAP = accuracy['mAP']
    sharpness = []
    contrast = []
    variance = []
    for index in indexes:
        res = handle_frame0(path, weight, caches, index, accuracy=False)
        sharpness.append(res['sharpness'])
        contrast.append(res['contrast'])
        variance.append(res['variance'])
    return {'bitrate': bitrate, 'mAP': mAP, 'sharpness': np.mean(sharpness), 'contrast': np.mean(contrast), 'variance': np.mean(variance)}


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
    with Pool(12) as pool:
        res = pool.starmap(handle_frames, [(bitrate, path, weight, caches) for bitrate, path in records[resolution].items()])
    print(res)


if __name__ == '__main__':
    main()

