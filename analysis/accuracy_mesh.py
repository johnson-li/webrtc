import argparse
import json
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from utils.cache import cache, read_cache
from utils.files import get_meta, get_meta_dict
from utils.const import get_resolution, get_resolution0
from utils.base import RESULT_IMAGE_PATH, RESULT_DIAGRAM_PATH
from analysis.dataset import get_ground_truth
from utils.metrics.iou import bbox_iou
from analysis.main import coco_class_to_waymo
from multiprocessing import Pool
from utils.plot import init_figure_wide


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to analyse accuracy in detail.')
    parser.add_argument('-d', '--path', default=os.path.expanduser('~/Data/webrtc_exp3'), help='Data path')
    parser.add_argument('-w', '--weight', default='yolov5s', help='The weight of YOLO',
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
                if data and coco_class_to_waymo(data['detection']['cls_pred']) > 0:
                    sequence = data['frame_sequence']
                    detections.setdefault(sequence, []).append(data['detection'])
    return detections


def get_bbox(d):
    return d['x1'], d['y1'], d['x2'], d['y2']


def handle_frame(detections, ground_truth, resolution):
    res = {'data': [],
           'detection_num': len(detections),
           }
    for gt in ground_truth:
        ious = []
        cls = gt['cls']
        for detection in detections:
            cls_pred = detection['cls_pred']
            cls_pred = coco_class_to_waymo(cls_pred)
            if cls == cls_pred:
                det = np.array(get_bbox(detection)) * 1920 / resolution[0]
                iou = bbox_iou(det, np.array([get_bbox(gt), ]))[0]
                ious.append((iou, detection,))
        ious = filter(lambda x: x[0] > 0, ious)
        ious = sorted(ious, key=lambda x: x[0])
        if ious:
            iou, det = ious[-1]
            detections.remove(det)
        else:
            iou, det = 0, None
        res['data'].append({'ground_truth': gt, 'IOU': iou, 'detection': det})
    res['ground_truth_num'] = len(ground_truth)
    res['iou_list'] = [d['IOU'] for d in res['data'] if d['IOU'] > 0]
    res['conf_list'] = [d['detection']['conf'] for d in res['data'] if d['IOU'] > 0]
    res['iou_median'] = np.median(res['iou_list'])
    res['conf_median'] = np.median(res['conf_list'])
    res['recognise_ratio'] = len([d for d in res['data'] if d['IOU'] > 0]) / len(ground_truth)
    res['recognise_ratio2'] = f"{len([d for d in res['data'] if d['IOU'] > 0])} / {len(ground_truth)}"
    res.pop('data')
    return res


def convert_detection(detection, resolution):
    res = detection.copy()
    res['x1'] = detection['x1'] * resolution[0]
    res['x2'] = detection['x2'] * resolution[0]
    res['y1'] = detection['y1'] * resolution[1]
    res['y2'] = detection['y2'] * resolution[1]
    return res


def handle(path, weight, ground_truth, sequences=[], resolutions=[]):
    meta_file = os.path.join(path, "metadata.txt")
    if os.path.isfile(meta_file):
        meta = get_meta(meta_file)
        resolution = [int(x) for x in meta['resolution'].split('x')]
        bitrate = meta['bitrate']
        is_baseline = False
    else:
        resolution = path.split('/')[-1].split('_')[-1]
        resolution = get_resolution0(resolution)
        is_baseline = True
        bitrate = 12000
    if f'{resolution[0]}p' not in resolutions:
        return None
    dump_dir = os.path.join(path, 'dump')
    detections = load_detections(dump_dir, weight, sequences)
    detections = {int(k): [convert_detection(vv, resolution) for vv in v] for k, v in detections.items()}
    res = {}
    for seq in detections.keys():
        res[seq] = handle_frame(detections[seq], ground_truth[seq], resolution)
    res.update({
        'is_baseline': is_baseline,
        'resolution': resolution,
        'bitrate': bitrate,
    })
    return res


# @cache
def work(path, weight, sequences, resolutions):
    parallel = True
    dirs = os.listdir(path)
    dirs = list(filter(lambda x: len(os.listdir(os.path.join(os.path.join(path, x), 'dump'))) > 20, dirs))
    ground_truth = get_ground_truth(limit=800)
    ground_truth = {int(k): v for k, v in ground_truth.items()}
    if sequences:
        ground_truth = {s: ground_truth[s] for s in sequences}
    if parallel:
        pool = Pool(12)
        res = \
            pool.starmap(handle, [(os.path.join(path, d), weight, ground_truth, sequences, resolutions) for d in dirs])
    else:
        res = []
        for d in dirs:
            r = handle(os.path.join(path, d), weight, ground_truth, sequences, resolutions)
            res.append(r)
    res = list(filter(lambda x: x, res))
    return res


def main():
    sequences = []
    resolutions = ['1920p']
    args = parse_args()
    res = work(args.path, args.weight, sequences, resolutions)
    print("Start illustration")
    illustrate(sequences, resolutions, args.path, args.weight)


def merge(statics, sequences):
    res = {}
    if sequences:
        sequences = [str(s) for s in sequences]
        statics = [statics[str(s)] for s in sequences if s in statics]
    else:
        statics = list(statics.values())
    if not statics:
        return {}
    keys = statics[0].keys()
    for k in keys:
        if k.endswith('list'):
            res.setdefault(k, [])
            for s in statics:
                res[k] += s[k]
        else:
            res[k] = np.nanmedian([s[k] for s in statics])
    return res


def draw_diagram(key, data, resolution):
    data = data[resolution]
    data = {int(k): v for k, v in data.items()}
    keys = sorted(data.keys())
    values = [data[k] for k in keys]
    if key.endswith('list'):
        fig, ax, font_size = init_figure_wide((11, 5))
        median_val = np.array([np.median(v) for v in values])
        top_val = np.array([np.percentile(v, 90) for v in values])
        bottom_val = np.array([np.percentile(v, 10) for v in values])
        yerr = (median_val - bottom_val, top_val - median_val)
        plt.bar([str(k / 1000) for k in keys], [np.median(v) for v in values],
                yerr=yerr)
        # plt.title(key)
        plt.xlabel('Bitrate (Mbps)')
        if key == 'conf_list':
            plt.ylabel('Confidence')
        elif key == 'iou_list':
            plt.ylabel('IOU')
        plt.tight_layout(pad=.3)
        plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'accuracy_{key}.pdf'))
        plt.show()
    else:
        fig, ax, font_size = init_figure_wide((6, 3.5))
        if key == 'recognise_ratio':
            values = [v * 100 for v in values]
        plt.plot([k / 1000 for k in keys], values, linewidth=2)
        # plt.title(key)
        plt.xlabel('Bitrate (Mbps)', fontsize=font_size)
        if key == 'recognise_ratio':
            plt.ylabel('Recognized objects (%)', fontsize=font_size)
        elif key == 'conf_median':
            plt.ylabel('Confidence', fontsize=font_size)
        elif key == 'iou_median':
            plt.ylabel('IOU', fontsize=font_size)
        plt.tight_layout(pad=.3)
        plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'accuracy_{key}.pdf'))
        # plt.show()


def draw_figure(sequence, resolution, path, weight):
    meta_dict = get_meta_dict(path)
    meta_dict = {int(k): v for k, v in meta_dict[resolution].items()}
    print(f'Meta dict: {meta_dict}')
    width, height = get_resolution(resolution)
    plt.figure(1)
    ground_truth = get_ground_truth(sequence, 1)[str(sequence)]
    for index, bitrate in enumerate(sorted(meta_dict.keys())):
        path = meta_dict[bitrate]
        detections = load_detections(os.path.join(path, 'dump'), weight, [sequence])
        detections = {int(k): v for k, v in detections.items()}
        detections = detections[sequence]
        image_path = os.path.join(path, f'dump/{sequence}.bin')
        image = np.fromfile(image_path)
        image = np.frombuffer(image, dtype=np.uint8).reshape((height, width, -1))  # BGRA
        image = image[:, :, :3][:, :, ::-1]
        ax = plt.gca()
        plt.imshow(image)
        plt.axis('off')
        plt.title(bitrate)
        ax.patches = []
        for detection in detections:
            x1, y1, x2, y2 = [detection[k] for k in ['x1', 'y1', 'x2', 'y2']]
            x1, y1, x2, y2 = x1 * width, y1 * height, x2 * width, y2 * height
            rect = patches.Rectangle((x1, y1), x2 - x1, y2 - y1, linewidth=.5, edgecolor='r', facecolor='none')
            ax.add_patch(rect)
        for gt in ground_truth:
            x1, y1, x2, y2 = [gt[k] for k in ['x1', 'y1', 'x2', 'y2']]
            rect = patches.Rectangle((x1, y1), x2 - x1, y2 - y1, linewidth=.3, edgecolor='g', facecolor='none')
            ax.add_patch(rect)
        path = os.path.join(RESULT_IMAGE_PATH, f'codec_{bitrate}.png')
        plt.savefig(path, dpi=600)
        print(f'Write image to file: {path}, number of detections: {len(detections)}, '
              f'number of ground truth: {len(ground_truth)}')


def illustrate(sequences, resolutions, path, weight):
    res = read_cache(work)
    data = {}
    # if len(sequences) == 1 and len(resolutions) == 1:
    #     draw_figure(sequences[0], resolutions[0], path, weight)
    for r in res:
        resolution = f"{r['resolution'][0]}p"
        bitrate = r['bitrate']
        for seq, statics in r.items():
            if seq in ('resolution', 'bitrate', 'is_baseline'):
                continue
            data.setdefault(resolution, {}).setdefault(bitrate, {})[seq] = \
                {k: statics[k] for k in ['iou_median', 'recognise_ratio', 'conf_median', 'iou_list', 'conf_list']}
    data2 = {}
    for resolution, v in data.items():
        for bitrate, statics in v.items():
            statics = merge(statics, sequences)
            for k, v in statics.items():
                data2.setdefault(k, {}).setdefault(resolution, {})[bitrate] = v
    for k, v in data2.items():
        for resolution in resolutions:
            draw_diagram(k, v, resolution)


if __name__ == '__main__':
    main()
