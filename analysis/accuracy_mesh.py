import argparse
import json
import os
import numpy as np
import matplotlib.pyplot as plt
from utils.cache import cache, read_cache
from pprint import pprint
from utils.files import get_meta
from utils.const import get_resolution
from analysis.dataset import get_ground_truth
from utils.metrics.iou import bbox_iou
from analysis.main import coco_class_to_waymo

SEQUENCES = [180, 181]


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to analyse accuracy in detail.')
    parser.add_argument('-d', '--path', default=os.path.expanduser('~/Data/webrtc_exp3'), help='Data path')
    parser.add_argument('-w', '--weight', default='yolov5x', help='The weight of YOLO',
                        choices=['yolov5x', 'yolov5s', 'yolov5l'])
    args = parser.parse_args()
    return args


def load_detections(path, weight, sequences=[]):
    detections = {}
    paths = []
    for sequence in sequences:
        det_path = os.path.join(path, f'{sequence}.{weight}.txt')
        if os.path.isfile(det_path):
            paths.append(det_path)
    if not sequences:
        for det_path in filter(lambda x: x.endswith(f'.{weight}.txt'), os.listdir(path)):
            det_path = os.path.join(path, det_path)
            paths.append(det_path)
    for det_path in paths:
        with open(det_path) as f:
            for line in f.readlines():
                data = json.loads(line)
                sequence = data['frame_sequence']
                detections.setdefault(sequence, []).append(data['detection'])

    return detections


def get_bbox(d):
    return d['x1'], d['y1'], d['x2'], d['y2']


def handle_frame(detections, ground_truth):
    res = {'data': []}
    for gt in ground_truth:
        ious = []
        cls = gt['cls']
        for detection in detections:
            cls_pred = detection['cls_pred']
            cls_pred = coco_class_to_waymo(cls_pred)
            if cls == cls_pred:
                iou = bbox_iou(get_bbox(detection), np.array([get_bbox(gt), ]))[0]
                ious.append((iou, detection))
        ious = filter(lambda x: x[0] > 0, ious)
        ious = sorted(ious, key=lambda x: x[0])
        if ious:
            iou, det = ious[-1]
            detections.remove(det)
        else:
            iou, det = 0, None
        res['data'].append({'ground_truth': gt, 'IOU': iou, 'detection': det})
    res['ground_truth_num'] = len(ground_truth)
    res['detection_num'] = len(detections)
    res['iou_median'] = np.median([d['IOU'] for d in res['data'] if d['IOU'] > 0])
    res['recognise_ratio'] = len([d for d in res['data'] if d['IOU'] > 0]) / len(ground_truth)
    res.pop('data')
    return res


def convert_detection(detection, resolution):
    res = detection.copy()
    res['x1'] = detection['x1'] * resolution[0]
    res['x2'] = detection['x2'] * resolution[0]
    res['y1'] = detection['y1'] * resolution[1]
    res['y2'] = detection['y2'] * resolution[1]
    return res


def handle(path, weight, ground_truth, sequences=[]):
    meta_file = os.path.join(path, "metadata.txt")
    if os.path.isfile(meta_file):
        meta = get_meta(meta_file)
        resolution = [int(x) for x in meta['resolution'].split('x')]
        bitrate = meta['bitrate']
        is_baseline = False
    else:
        resolution = path.split('_')[-1]
        resolution = get_resolution(resolution)
        is_baseline = True
        bitrate = 12000
    dump_dir = os.path.join(path, 'dump')
    detections = load_detections(dump_dir, weight, sequences)
    detections = {int(k): [convert_detection(vv, resolution) for vv in v] for k, v in detections.items()}
    res = {}
    for seq in detections.keys():
        res[seq] = handle_frame(detections[seq], ground_truth[seq])
    res.update({
        'is_baseline': is_baseline,
        'resolution': resolution,
        'bitrate': bitrate,
    })
    return res


@cache
def work(args):
    dirs = os.listdir(args.path)
    dirs = list(filter(lambda x: len(os.listdir(os.path.join(os.path.join(args.path, x), 'dump'))) > 20, dirs))
    ground_truth = get_ground_truth(limit=800)
    ground_truth = {int(k): v for k, v in ground_truth.items()}
    if SEQUENCES:
        ground_truth = {s: ground_truth[s] for s in SEQUENCES}
    res = []
    for d in dirs:
        r = handle(os.path.join(args.path, d), args.weight, ground_truth, SEQUENCES)
        res.append(r)
    pprint(res)
    return res


def main():
    args = parse_args()
    work(args)


def merge(statics, sequences):
    res = {}
    sequences = [str(s) for s in sequences]
    statics = [statics[str(s)] for s in sequences if s in statics]
    if not statics:
        return {}
    keys = statics[0].keys()
    for k in keys:
        res[k] = np.median([s[k] for s in statics])
    return res


def draw(key, data):
    data = data['1920p']
    data = {int(k): v for k, v in data.items()}
    keys = sorted(data.keys())
    values = [data[k] for k in keys]
    plt.plot(keys, values)
    plt.title(key)
    plt.show()


def illustrate():
    res = read_cache(work)
    data = {}
    for r in res:
        resolution = f"{r['resolution'][0]}p"
        bitrate = r['bitrate']
        for seq, statics in r.items():
            if seq in ('resolution', 'bitrate', 'is_baseline'):
                continue
            data.setdefault(resolution, {}).setdefault(bitrate, {})[seq] = \
                {'iou_median': statics['iou_median'], 'recognise_ratio': statics['recognise_ratio']}
    sequences = SEQUENCES
    data2 = {}
    for resolution, v in data.items():
        for bitrate, statics in v.items():
            statics = merge(statics, sequences)
            for k, v in statics.items():
                data2.setdefault(k, {}).setdefault(resolution, {})[bitrate] = v
    for k, v in data2.items():
        draw(k, v)


if __name__ == '__main__':
    # main()
    illustrate()
