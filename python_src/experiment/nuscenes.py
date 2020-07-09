import os
import re
import sys
import cv2
import time
import logging
import argparse
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from experiment.dataset import DataSet

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
DATA_PATH = os.path.expanduser("~/Data/nuscenes")
FRAME_PATH = os.path.join(DATA_PATH, 'sweeps/CAM_FRONT')
CACHE_PATH = '/tmp/nuscenes_images'
logger = logging.getLogger(__name__)


class Nuscenes(DataSet):
    def __init__(self):
        super(Nuscenes, self).__init__('nuScenes')

    def cache_images(self):
        Path(CACHE_PATH).mkdir(parents=True, exist_ok=True)
        frames_path = os.path.join(FRAME_PATH, 'list.txt')
        index = 0
        for file_name in filter(lambda x: x, open(frames_path, 'r').read().split('\n')):
            file_path = os.path.join(FRAME_PATH, file_name)
            result = re.match('([a-z0-9-]+)__([A-Z_]+)__([0-9]+).jpg', file_name)
            timestamp = int(result.groups()[2])
            if os.path.isfile(file_path):
                target_path = os.path.join(CACHE_PATH, '%04d_%d.npy' % (index, timestamp))
                if not os.path.isfile(target_path):
                    img = cv2.imdecode(np.fromfile(file_path), cv2.IMREAD_UNCHANGED)  # shape: height x width x channel
                    np.save(target_path, img)
            index += 1
            if index % 200 == 0:
                logger.info('Cached %d images' % index)
            if index >= 20 * 60:  # One minute for 20 FPS
                break

    def images(self):
        files = os.listdir(CACHE_PATH)
        files = [f.split('.')[0].split('_') for f in files]
        files.sort(key=lambda f: f[0])
        for i, timestamp in files:
            i, timestamp = int(i), int(timestamp)
            frame_path = os.path.join(CACHE_PATH, '%04d_%d.npy' % (i, timestamp))
            if not os.path.isfile(frame_path):
                break
            # logger.info('Feed %s to webcam' % frame_path)
            image = np.load(frame_path)
            yield image, timestamp


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to manipulate and illustrate the nuScenes data set.')
    parser.add_argument('-i', '--illustrate', action='store_true', help='Illustrate the date set')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    dataset = Nuscenes()
    dataset.cache_images()
    if args.illustrate:
        figure = plt.figure(figsize=(9, 6), dpi=100)
        ax = figure.gca()
        im = None
        index = 0
        start_ts1 = time.time()
        start_ts2 = 0
        for img, timestamp in dataset.images():
            if not im:
                im = ax.imshow(img)
            else:
                im.set_data(img)
            plt.draw()
            if not start_ts2:
                start_ts2 = timestamp
            # print((timestamp - start_ts2) / 1000000.0, time.time() - start_ts1)
            wait = max(.001, (timestamp - start_ts2) / 1000000.0 - (time.time() - start_ts1))
            plt.pause(.001)
            time.sleep(wait - .001)
            index += 1
            if index > 100:
                break


if __name__ == '__main__':
    main()
