import json
import os
from experiment.config import *
from experiment.base import *
from waymo_open_dataset import dataset_pb2 as open_dataset

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import tensorflow as tf


def get_datasets(limit=10000):
    dataset = json.load(open(os.path.join(RESOURCE_PATH, 'dataset.json'), 'r'))
    result = []
    index = 0
    for d in dataset:
        path = os.path.join(os.path.expanduser('~/Data/waymo/training_0000'), d)
        dataset = tf.data.TFRecordDataset(path, compression_type='')
        result.append(dataset)
        index += 1
        if index >= limit:
            break
    return result


def get_ground_truth(offset=0, limit=999999):
    dataset = json.load(open(os.path.join(RESOURCE_PATH, 'dataset.json'), 'r'))
    result = {}
    index = 0
    for d in dataset:
        path = os.path.join(os.path.expanduser('~/Data/waymo/training_0000'), d)
        record = tf.data.TFRecordDataset(path, compression_type='')
        for data in record:
            frame = open_dataset.Frame()
            frame.ParseFromString(bytearray(data.numpy()))
            labels = frame.camera_labels[0].labels
            res = []
            for label in labels:
                box = label.box
                res.append({'x1': box.center_x - box.length / 2, 'y1': box.center_y - box.width / 2,
                            'x2': box.center_x + box.length / 2, 'y2': box.center_y + box.width / 2,
                            'cls': label.type})
            if index < offset:
                index += 1
                continue
            result[index] = res
            index += 1
            if index > limit:
                break
        if index > limit:
            break
    return result


def load_classes(filename):
    fp = open(os.path.join(RESOURCE_PATH, filename), "r")
    names = fp.read().split("\n")[:-1]
    return names


CLASSES = load_classes('coco.names')
WAYMO_CLASSES = load_classes('waymo.names')
