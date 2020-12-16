import argparse
import os
from pathlib import Path
import numpy as np
import json
import cv2
from experiment.base import RESOURCE_PATH
from multiprocessing import Pool

RESOLUTION = (1920, 1280)
CACHE_DIR = os.path.expanduser('~/Data/waymo/cache')
CACHED_FILES = []


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to generate the baseline folder.')
    parser.add_argument('-p', '--path', default=os.path.expanduser('~/Data/webrtc_exp3'), help='Data directory')
    args = parser.parse_args()
    return args


def read_image(cache, frame_sequence):
    image = np.load(cache[frame_sequence])
    image = np.frombuffer(image, dtype=np.uint8).reshape((RESOLUTION[1], RESOLUTION[0], -1))  # BGRA
    return image


def generate(parent, cache, frame_sequence, scale):
    print(f'Dump baseline of sequence: {frame_sequence}, scale: {scale}')
    width, height = [int(i * scale) for i in RESOLUTION]
    path_name = f'baseline_{width}p'
    path = os.path.join(parent, path_name)
    dump_path = os.path.join(path, 'dump')
    Path(dump_path).mkdir(parents=True, exist_ok=True)
    img_path = os.path.join(dump_path, f'{frame_sequence}.bin')
    json_path = os.path.join(dump_path, f'{frame_sequence}.json')
    json.dump({'timestamp': -1, 'width': width, 'height': height}, open(json_path, 'w+'))
    image = read_image(cache, frame_sequence)
    image = cv2.resize(image, dsize=(width, height), interpolation=cv2.INTER_CUBIC)
    image = image[:, :, ::-1]
    with open(img_path, 'wb+') as f:
        image.astype('uint8').tofile(f)


def main():
    args = parse_args()
    image_files = json.load(open(os.path.join(RESOURCE_PATH, 'dataset.json'), 'r'))
    frame_sequences = set()
    for f in image_files:
        f = os.path.join(CACHE_DIR, f)
        ff = sorted([i for i in os.listdir(f) if i.endswith('npy')], key=lambda x: int(x.split('.')[0]))
        CACHED_FILES.extend([os.path.join(f, i) for i in ff])
    for f in os.listdir(args.path):
        if f.startswith('baseline'):
            continue
        f = os.path.join(args.path, f)
        f = os.path.join(f, 'dump')
        for i in [int(i.split('.')[0]) for i in os.listdir(f) if i.endswith('.bin')]:
            frame_sequences.add(i)
    frame_sequences = sorted(list(frame_sequences))
    target_width = [480, 720, 960, 1200, 1440, 1680, 1920]
    scales = [w / 1920 for w in target_width]
    pool = Pool(10)
    params = []
    for frame_sequence in frame_sequences:
        for scale in scales:
            params.append((args.path, CACHED_FILES, frame_sequence, scale))
    pool.starmap(generate, params)
    print(f'Dumped scales: {scales}')


if __name__ == '__main__':
    main()
