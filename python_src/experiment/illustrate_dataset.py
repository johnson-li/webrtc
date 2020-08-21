import os
import cv2
import time
import timeit
import asyncio
import pathlib
import argparse
from multiprocessing import Process, Pipe
from experiment.waymo import WaymoDataSet
from experiment.bdd import BddDataSet
from experiment.dataset import DataSet

FPS = 10
DATASET = DataSet()


def do_compress(image, index):
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
    start_ts = time.monotonic() * 1000
    retusl, encimg = cv2.imencode('.jpg', image, encode_param)
    print(f'JPEG encoding produces {encimg.shape[0]} bytes and costs {time.monotonic() * 1000 - start_ts} ms.')


def feed_jpeg_compress(index, start_ts, image):
    ts = timeit.default_timer()
    offset_ts = ts - start_ts
    if offset_ts > 1 / FPS * (index + 1):
        print('Frame dropped')
        return
    elif offset_ts < 1 / FPS * index:
        time.sleep(1 / FPS * index - offset_ts)
        do_compress(image, index)
    else:
        do_compress(image, index)


def jpeg_compress():
    index = 0
    DATASET.cache_images()
    print("Images are all cached")
    start_ts = timeit.default_timer()
    for image in DATASET.images(logging=False):
        feed_jpeg_compress(index, start_ts, image)
        index += 1


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to compress the dataset into jpeg.')
    parser.add_argument('-d', '--dataset', choices=['waymo', 'bdd'], default='waymo', help='the data set to use')
    parser.add_argument('-f', '--fps', type=int, default=10, help='the number of frames per second')
    args = parser.parse_args()
    global DATASET, FPS
    if args.dataset == 'waymo':
        DATASET = WaymoDataSet()
    elif args.dataset == 'bdd':
        DATASET = BddDataSet()
    FPS = args.fps
    return args


def main():
    args = parse_args()
    jpeg_compress()


if __name__ == '__main__':
    main()
