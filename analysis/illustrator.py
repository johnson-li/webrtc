import argparse
import os
from experiment.config import *
from experiment.base import *
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from analysis.dataset import get_datasets, load_classes
from waymo_open_dataset import dataset_pb2 as open_dataset
from analysis.parser import parse_results_accuracy
from experiment.logging import logging

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import tensorflow as tf

logger = logging.getLogger(__name__)
figure = plt.figure(figsize=(9, 6), dpi=200)
ax = figure.gca()
IM = None
CLASSES = load_classes()
WAYMO_CLASSES = ['Unknown', 'Vehicle', 'Pedestrian', 'Sign', 'Cyclist']
WIDTH = 1920
HEIGHT = 1280


def draw_frame_image(frame):
    global IM
    if not IM:
        IM = ax.imshow(frame)
        plt.show(block=False)
    else:
        IM.set_data(frame)


def draw_frame_boxes_waymo(labels):
    for label in labels:
        cls = label.type
        cls_name = label.Type.Name(cls)
        box = label.box
        x1 = box.center_x - box.length / 2
        y1 = box.center_y - box.width / 2
        x2 = box.center_x + box.length / 2
        y2 = box.center_y + box.width / 2
        color = 'red' if cls == 1 else 'yellow' if cls == 2 else 'blue' if cls == 3 else 'black'
        rect = patches.Rectangle((x1, y1), x2 - x1, y2 - y1, linewidth=1, edgecolor=color, facecolor='none')
        ax.add_patch(rect)


def draw_frame_boxes_yolo(detections, frame_sequence):
    if frame_sequence not in detections:
        logger.warning("No detection on frame #%d" % frame_sequence)
        return
    detection = detections[frame_sequence]['detection']
    for detc in detection:
        box = detc['box']
        cls = detc['class']
        cls_name = detc['class_name']
        x1, y1, x2, y2 = box
        x1 *= WIDTH
        x2 *= WIDTH
        y1 *= HEIGHT
        y2 *= HEIGHT
        rect = patches.Rectangle((x1, y1), x2 - x1, y2 - y1, linewidth=1, edgecolor='white', facecolor='none')
        ax.add_patch(rect)


def illustrate(ground_truth=True, prediction_path=None):
    frame_sequence = 0
    datasets = get_datasets(limit=20)
    detections = parse_results_accuracy(prediction_path) if prediction_path else None
    for dataset in datasets:
        for record in dataset:
            frame = open_dataset.Frame()
            frame.ParseFromString(bytearray(record.numpy()))
            image = frame.images[0].image
            image = tf.image.decode_jpeg(image).numpy()
            for p in reversed(ax.patches):
                p.remove()
            draw_frame_image(image)
            if ground_truth:
                labels = frame.camera_labels[0].labels
                draw_frame_boxes_waymo(labels)
            if detections:
                draw_frame_boxes_yolo(detections, frame_sequence)
            plt.draw()
            plt.pause(.001)
            frame_sequence += 1


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to illustrate detection results and ground truth.')
    parser.add_argument('-f', '--folder', help='The result folder to illustrate')
    parser.add_argument('-g', '--ground-truth', help='Illustrate the ground truth', action='store_true')
    return parser.parse_args()


def main():
    args = parse_args()
    folder = args.folder
    illustrate(args.ground_truth, folder)


if __name__ == '__main__':
    main()
