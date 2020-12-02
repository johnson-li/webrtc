import os
import cv2
import json
import numpy as np
import argparse
import imageio
from utils.base import RESULT_DIAGRAM_PATH
from matplotlib import pyplot as plt
from analysis.main import analyse_accuracy
from analysis.parser import on_data
from multiprocessing import Pool
from utils.files import get_meta

CACHE_PATH = os.path.expanduser('~/Data/waymo/cache')
IMAGE_FILES = ["segment-10017090168044687777_6380_000_6400_000_with_camera_labels.tfrecord",
               "segment-10023947602400723454_1120_000_1140_000_with_camera_labels.tfrecord",
               "segment-1005081002024129653_5313_150_5333_150_with_camera_labels.tfrecord",
               "segment-10061305430875486848_1080_000_1100_000_with_camera_labels.tfrecord",
               "segment-10072140764565668044_4060_000_4080_000_with_camera_labels.tfrecord",
               'segment-10072231702153043603_5725_000_5745_000_with_camera_labels.tfrecord',
               'segment-10075870402459732738_1060_000_1080_000_with_camera_labels.tfrecord',
               'segment-10082223140073588526_6140_000_6160_000_with_camera_labels.tfrecord',
               'segment-10094743350625019937_3420_000_3440_000_with_camera_labels.tfrecord',
               ]


def load_caches():
    caches = []
    for d in IMAGE_FILES:
        d = os.path.join(CACHE_PATH, d)
        for i in range(1000):
            path = os.path.join(d, f'{i}.npy')
            if os.path.isfile(path):
                caches.append(path)
    return caches


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', type=str, default=os.path.expanduser('~/Data/webrtc_exp8'),
                        help='the path of experiment dir, which should contain two subfolders: baseline and latest')
    parser.add_argument('-w', '--weight', type=str, default='yolov5s', help='the name of the weight')
    opt = parser.parse_args()
    return opt


def read_dets(path):
    dets = []
    with open(path) as f:
        for line in f.readlines():
            dets.append(json.loads(line))
    return dets


def draw_histogram(img, name, gray=False):
    colors = ("r", "g", "b")
    channel_ids = (0, 1, 2)
    plt.figure()
    plt.title("Image Histogram")
    plt.xlabel("Pixel value [0-255]")
    plt.ylabel("Number of pixels")
    plt.ylim(0, 100000)
    if gray:
        for channel_id, c in zip(channel_ids, colors):
            histogram, bin_edges = np.histogram(img[:, :, channel_id], bins=256, range=(0, 256))
            plt.plot(bin_edges[0:-1], histogram, color=c)
    else:
        histogram, bin_edges = np.histogram(img, bins=256, range=(0, 256))
        plt.plot(bin_edges[0:-1], histogram)
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'histogram_{name}.png'), dpi=600)


def get_sharpness(img, gray_scale=False):
    if gray_scale:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    return cv2.Laplacian(img, cv2.CV_64F).var()


def get_contrast(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return gray.std()


def get_accuracy(detcs):
    detections = {}
    for detc in detcs:
        on_data(detections, detc)
    return analyse_accuracy(detections)


def handle_frame0(path, weight, caches, frame_sequence, baseline=False):
    width = 1920
    height = 1280
    dump_dir = os.path.join(path, 'dump')
    det_path = os.path.join(dump_dir, f'{frame_sequence}.{weight}.txt')
    if not os.path.isfile(det_path):
        return {}
    meta_path = os.path.join(path, 'metadata.txt')
    if os.path.isfile(meta_path):
        meta = get_meta(meta_path)
        width, height = [int(i) for i in meta['resolution'].split('x')]
    dets = read_dets(det_path)
    if baseline:
        img = np.load(caches[frame_sequence])
    else:
        img = np.fromfile(os.path.join(dump_dir, f'{frame_sequence}.bin'), dtype=np.uint8).reshape((height, width, -1))
        img = np.frombuffer(img, dtype=np.uint8).reshape((height, width, -1))[:, :, :3][:, :, ::-1]
    sharpness = get_sharpness(img)
    contrast = get_contrast(img)
    mAP = get_accuracy(dets)['mAP']
    return {'sharpness': sharpness, 'contrast': contrast, 'mAP': mAP}


def handle_frame(path, weight, caches, frame_sequence, size):
    print(f'Handle frame: {frame_sequence}')
    width, height = size
    dump_dir = os.path.join(path, 'latest/dump')
    baseline_dir = os.path.join(path, 'baseline')
    res_raw = os.path.join(baseline_dir, f'{frame_sequence}.{weight}.txt')
    res_yolo = os.path.join(dump_dir, f'{frame_sequence}.{weight}.txt')
    if not os.path.isfile(res_raw) or not os.path.isfile(res_yolo):
        return {}
    dets_raw = read_dets(res_raw)
    dets_yolo = read_dets(res_yolo)
    img_raw = np.load(caches[frame_sequence])
    img_yolo = np.fromfile(os.path.join(dump_dir, f'{frame_sequence}.bin'), dtype=np.uint8).reshape((height, width, -1))
    img_yolo = np.frombuffer(img_yolo, dtype=np.uint8).reshape((height, width, -1))[:, :, :3][:, :, ::-1]
    # imageio.imsave(f'{RESULT_DIAGRAM_PATH}/img_raw.jpg', img_raw)
    # imageio.imsave(f'{RESULT_DIAGRAM_PATH}/img_yolo.jpg', img_yolo)

    # draw_histogram(img_raw, 'raw')
    # draw_histogram(img_yolo, 'yolo')
    sharpness_raw = get_sharpness(img_raw)
    sharpness_yolo = get_sharpness(img_yolo)
    # print(f'Sharpness: raw: {sharpness_raw}, yolo: {sharpness_yolo}')
    contrast_raw = get_contrast(img_raw)
    contrast_yolo = get_contrast(img_yolo)
    # print(f'Contrast: raw: {contrast_raw}, yolo: {contrast_yolo}')

    mAP_raw = get_accuracy(dets_raw)['mAP']
    mAP_yolo = get_accuracy(dets_yolo)['mAP']
    return {'sharpness': [sharpness_raw, sharpness_yolo], 'contrast': [contrast_raw, contrast_yolo],
            'mAP': [mAP_raw, mAP_yolo]}


def main():
    opt = parse_args()
    caches = load_caches()
    path = opt.path
    dump_dir = os.path.join(path, 'latest/dump')
    baseline_dir = os.path.join(path, 'baseline')
    ids = list(set([i.split('.')[0] for i in os.listdir(baseline_dir)]))
    ids = [int(i) for i in ids if i.isnumeric()]

    # handle_frame(opt, 39)
    with Pool(11) as p:
        res = p.starmap(handle_frame, [(opt.path, opt.weight, caches, i) for i in ids])
    print(res)
    json.dump(res, open(os.path.join(RESULT_DIAGRAM_PATH, 'res.json'), 'w+'))


if __name__ == '__main__':
    main()
