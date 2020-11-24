import os
import json
import numpy as np
import argparse
import imageio


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
CACHES = []


def load_caches():
    count = 0
    for d in IMAGE_FILES:
        d = os.path.join(CACHE_PATH, d)
        for i in range(1000):
            path = os.path.join(d, f'{i}.npy')
            if os.path.isfile(path):
                CACHES.append(path)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', type=str, help='the path of experiment dir, which should contain two subfolders: baseline and latest')
    parser.add_argument('-w', '--weight', type=str, help='the name of the weight')
    opt = parser.parse_args()
    return opt


def read_dets(path):
    dets = []
    with open(path) as f:
        for line in f.readlines():
            dets.append(json.loads(line))
    return dets


def handle_frame(opt, frame_sequence):
    width = 1920
    height = 1280
    path = opt.path
    weight = opt.weight
    dump_dir = os.path.join(path, 'latest/dump')
    baseline_dir = os.path.join(path, 'baseline')
    res_raw = os.path.join(baseline_dir, f'{frame_sequence}.{weight}.txt')
    res_yolo = os.path.join(dump_dir, f'{frame_sequence}.{weight}.txt')
    dets_raw = read_dets(res_raw)
    dets_yolo = read_dets(res_yolo)
    img_raw = np.load(CACHES[frame_sequence])
    img_yolo = np.fromfile(os.path.join(dump_dir, f'{frame_sequence}.bin'))
    img_yolo = np.frombuffer(img_yolo, dtype=np.uint8).reshape((height, width, -1))[:, :, :3][:, :, ::-1].transpose(2, 0, 1).reshape((height, width, -1))
    img_yolo = np.ascontiguousarray(img_yolo)
    imageio.imsave('img_raw.jpg', img_raw)
    imageio.imsave('img_yolo.jpg', img_yolo)


def main():
    opt = parse_args()
    load_caches()
    path = opt.path
    dump_dir = os.path.join(path, 'latest/dump')
    baseline_dir = os.path.join(path, 'baseline')
    ids = list(set([i.split('.')[0] for i in os.listdir(baseline_dir)]))
    ids = [int(i) for i in ids if i.isnumeric()]
    handle_frame(opt, 331)


if __name__ == '__main__':
    main()

