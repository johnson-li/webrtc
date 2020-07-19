import argparse
import os
from experiment.config import *
from experiment.base import *
import numpy as np
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from analysis.dataset import get_datasets, CLASSES, WAYMO_CLASSES
from waymo_open_dataset import dataset_pb2 as open_dataset
from waymo_open_dataset.utils import frame_utils
from analysis.parser import parse_results_accuracy
from experiment.logging import logging

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import tensorflow as tf

logger = logging.getLogger(__name__)
figure = plt.figure(figsize=(9, 6), dpi=200)
ax = figure.gca()
IM = None
WIDTH = 1920
HEIGHT = 1280
OBJECT_SIZE_THRESHOLD = 0


def draw_frame_image(frame):
    global IM
    if not IM:
        IM = ax.imshow(frame)
        plt.show(block=False)
    else:
        IM.set_data(frame)


def draw_frame_boxes_waymo(labels, cls_list=None):
    for label in labels:
        cls = label.type
        if cls_list and cls not in cls_list:
            continue
        cls_name = label.Type.Name(cls)
        box = label.box
        x1 = box.center_x - box.length / 2
        y1 = box.center_y - box.width / 2
        x2 = box.center_x + box.length / 2
        y2 = box.center_y + box.width / 2
        if (x2 - x1) * (y2 - y1) < OBJECT_SIZE_THRESHOLD:
            continue
        color = 'red' if cls == 1 else 'yellow' if cls == 2 else 'blue' if cls == 3 else 'black'
        rect = patches.Rectangle((x1, y1), x2 - x1, y2 - y1, linewidth=1, edgecolor=color, facecolor='none')
        ax.add_patch(rect)


def draw_frame_boxes_yolo(detections, frame_sequence, cls_list=None):
    if frame_sequence not in detections:
        logger.warning("No detection on frame #%d" % frame_sequence)
        return
    detection = detections[frame_sequence]['detection']
    for detc in detection:
        box = detc['box']
        cls = detc['class']
        if cls_list and cls not in cls_list:
            continue
        cls_name = detc['class_name']
        x1, y1, x2, y2 = box
        x1 *= WIDTH
        x2 *= WIDTH
        y1 *= HEIGHT
        y2 *= HEIGHT
        if (x2 - x1) * (y2 - y1) < OBJECT_SIZE_THRESHOLD:
            continue
        rect = patches.Rectangle((x1, y1), x2 - x1, y2 - y1, linewidth=1, edgecolor='white', facecolor='none')
        ax.add_patch(rect)


def draw_labels(frame, frame_sequence, ground_truth, detections):
    text_var = plt.text(0, 0, '#%d' % frame_sequence)
    if ground_truth:
        labels = frame.camera_labels[0].labels
        draw_frame_boxes_waymo(labels)
    if detections:
        draw_frame_boxes_yolo(detections, frame_sequence)
    return text_var


def rgba(r):
    """Generates a color based on range.

    Args:
        r: the range value of a given point.
    Returns:
        The color for a given range
    """
    c = plt.get_cmap('jet')((r % 20.0) / 20.0)
    c = list(c)
    c[-1] = 0.5  # alpha
    return c


def plot_points_on_image(projected_points, rgba_func,
                         point_size=5.0):
    """Plots points on a camera image.

    Args:
        projected_points: [N, 3] numpy array. The inner dims are
            [camera_x, camera_y, range].
        rgba_func: a function that generates a color from a range value.
        point_size: the point size.

    """
    xs = []
    ys = []
    colors = []

    for point in projected_points:
        xs.append(point[0])  # width, col
        ys.append(point[1])  # height, row
        colors.append(rgba_func(point[2]))

    return plt.scatter(xs, ys, c=colors, s=point_size, edgecolors="none")


def draw_projection(frame, range_images, camera_projections, range_image_top_pose):
    points, cp_points = frame_utils.convert_range_image_to_point_cloud(
        frame,
        range_images,
        camera_projections,
        range_image_top_pose)
    points_ri2, cp_points_ri2 = frame_utils.convert_range_image_to_point_cloud(
        frame,
        range_images,
        camera_projections,
        range_image_top_pose,
        ri_index=1)
    # 3d points in vehicle frame.
    points_all = np.concatenate(points, axis=0)
    points_all_ri2 = np.concatenate(points_ri2, axis=0)
    # camera projection corresponding to each point.
    cp_points_all = np.concatenate(cp_points, axis=0)
    cp_points_all_ri2 = np.concatenate(cp_points_ri2, axis=0)

    cp_points_all_concat = np.concatenate([cp_points_all, points_all], axis=-1)
    cp_points_all_concat_tensor = tf.constant(cp_points_all_concat)

    # The distance between lidar points and vehicle frame origin.
    points_all_tensor = tf.norm(points_all, axis=-1, keepdims=True)
    cp_points_all_tensor = tf.constant(cp_points_all, dtype=tf.int32)

    mask = tf.equal(cp_points_all_tensor[..., 0], 1)

    cp_points_all_tensor = tf.cast(tf.gather_nd(
        cp_points_all_tensor, tf.where(mask)), dtype=tf.float32)
    points_all_tensor = tf.gather_nd(points_all_tensor, tf.where(mask))

    projected_points_all_from_raw_data = tf.concat(
        [cp_points_all_tensor[..., 1:3], points_all_tensor], axis=-1).numpy()

    return plot_points_on_image(projected_points_all_from_raw_data, rgba, point_size=2.0)


def illustrate(ground_truth=True, prediction_path=None):
    frame_sequence = 0
    datasets = get_datasets(limit=20)
    detections = parse_results_accuracy(prediction_path) if prediction_path else None
    for dataset in datasets:
        for record in dataset:
            frame = open_dataset.Frame()
            frame.ParseFromString(bytearray(record.numpy()))
            (range_images, camera_projections, range_image_top_pose) = \
                frame_utils.parse_range_image_and_camera_projection(frame)
            image = tf.image.decode_jpeg(frame.images[0].image).numpy()

            for p in reversed(ax.patches):
                p.remove()

            # Draw contents
            draw_frame_image(image)
            text_var = draw_labels(frame, frame_sequence, ground_truth, detections)
            scatter = draw_projection(frame, range_images, camera_projections, range_image_top_pose)

            plt.draw()
            plt.pause(.001)
            frame_sequence += 1
            text_var.set_visible(False)
            scatter.remove()


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to illustrate detection results and ground truth.')
    parser.add_argument('-f', '--folder', help='The result folder to illustrate')
    parser.add_argument('-g', '--ground-truth', help='Illustrate the ground truth', action='store_true')
    parser.add_argument('-m', '--min-object', type=int, help='The minimal size of the objects. Smaller ones, both '
                                                             'in the ground truth and the prediction, are ignored.')
    args = parser.parse_args()
    if args.min_object is not None:
        global OBJECT_SIZE_THRESHOLD
        OBJECT_SIZE_THRESHOLD = args.min_object
    return args


def main():
    args = parse_args()
    folder = args.folder
    illustrate(args.ground_truth, folder)


if __name__ == '__main__':
    main()
