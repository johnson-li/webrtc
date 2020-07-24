import os
import re
import sys
import time
import logging
import imageio
import argparse
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from experiment.dataset import DataSet

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
DATA_PATH = os.path.expanduser("~/Data/a2d2")
FRAME_PATH = os.path.join(DATA_PATH, 'camera_lidar_semantic_bboxes/20180807_145028/camera/cam_front_center')
LABEL_PATH = os.path.join(DATA_PATH, 'camera_lidar_semantic_bboxes/20180807_145028/label3D/cam_front_center')
CACHE_PATH = '/tmp/a2d2_images'
logger = logging.getLogger(__name__)


class A2D2(DataSet):
    def __init__(self):
        super().__init__('A2D2')

    def cache_images(self):
        Path(CACHE_PATH).mkdir(parents=True, exist_ok=True)
        frames_path = os.path.join(FRAME_PATH, 'list.txt')
        index = 0
        for file_name in filter(lambda x: x, open(frames_path, 'r').read().split('\n')):
            file_path = os.path.join(FRAME_PATH, file_name)
            result = re.match('[0-9]+_camera_[a-z]+_([0-9]+).png', file_name)
            timestamp = int(result.groups()[0])
            if os.path.isfile(file_path):
                target_path = os.path.join(CACHE_PATH, '%04d_%d.npy' % (index, timestamp))
                if not os.path.isfile(target_path):
                    img = imageio.imread(file_path)  # shape: height x width x channel
                    img = np.asarray(img)
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
            image = np.load(frame_path)
            yield image, timestamp


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to manipulate and illustrate the A2D2 data set.')
    parser.add_argument('-i', '--illustrate', action='store_true', help='Illustrate the date set')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    dataset = A2D2()
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
            print((timestamp - start_ts2) / 1000.0, time.time() - start_ts1)
            wait = max(.001, (timestamp - start_ts2) / 1000.0 - (time.time() - start_ts1))
            plt.pause(.001)
            time.sleep(wait - .001)
            index += 1
            if index > 100:
                break


if __name__ == '__main__':
    main()
