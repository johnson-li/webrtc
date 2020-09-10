import os
import pathlib
import numpy as np
from pathlib import Path
from experiment.dataset import DataSet
from waymo_open_dataset import dataset_pb2 as open_dataset

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import tensorflow as tf

DATA_PATH = os.path.expanduser('~/Data/waymo/training_0000')
PROJECT_PATH = os.path.dirname(os.path.dirname(pathlib.Path(__file__).parent.absolute()))
CACHE_PATH = '/tmp/waymo_images'
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


def load_dataset(filename):
    dataset = tf.data.TFRecordDataset(filename, compression_type='')
    images = []
    for data in dataset:
        frame = open_dataset.Frame()
        frame.ParseFromString(bytearray(data.numpy()))
        image = frame.images[0].image
        image = tf.image.decode_jpeg(image).numpy()
        images.append(image)
    return images


class WaymoDataSet(DataSet):
    def __init__(self):
        super(WaymoDataSet, self).__init__("Waymo")

    def cache_images(self):
        for filename in IMAGE_FILES:
            filepath = os.path.join(DATA_PATH, filename)
            cache_dir = os.path.join(CACHE_PATH, filename)
            flag_path = os.path.join(cache_dir, 'flag.txt')
            Path(cache_dir).mkdir(parents=True, exist_ok=True)
            if os.path.isfile(flag_path):
                with open(flag_path, 'r') as f:
                    flag = f.read()
                    if flag == '1':
                        print('TF record file is already cached: %s' % filename)
                        continue
            print('Cache TF record file: %s' % filename)
            images = load_dataset(filepath)
            for i, img in enumerate(images):
                path = os.path.join(cache_dir, '%d.npy' % i)
                np.save(path, img)
            with open(flag_path, 'w') as f:
                f.write('1')

    def images(self, logging=True):
        for filename in IMAGE_FILES:
            cache_dir = os.path.join(CACHE_PATH, filename)
            for i in range(100000):
                frame_path = os.path.join(cache_dir, '%d.npy' % i)
                if logging:
                    print('Feed %s to webcam' % frame_path)
                if not os.path.isfile(frame_path):
                    break
                image = np.load(frame_path)
                yield image
