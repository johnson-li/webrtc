import os
import tensorflow as tf
import math
import numpy as np
import itertools
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from waymo_open_dataset.utils import range_image_utils
from waymo_open_dataset.utils import transform_utils
from waymo_open_dataset.utils import  frame_utils
from waymo_open_dataset import dataset_pb2 as open_dataset


def show_camera_image(camera_image, camera_labels, layout, cmap=None):
  """Show a camera image and the given camera labels."""

  ax = plt.subplot(*layout)
  ax.clear()

  # Draw the camera labels.
  for labels in camera_labels:
    # Ignore camera labels that do not correspond to this camera.
    if labels.name != camera_image.name:
      continue

    # Iterate over the individual labels.
    for label in labels.labels:
      # Draw the object bounding box.
      ax.add_patch(patches.Rectangle(
        xy=(label.box.center_x - 0.5 * label.box.length,
          label.box.center_y - 0.5 * label.box.width),
        width=label.box.length,
        height=label.box.width,
        linewidth=1,
        edgecolor='red',
        facecolor='none'))

  plt.imshow(tf.image.decode_jpeg(camera_image.image), cmap=cmap)
  plt.title(open_dataset.CameraName.Name.Name(camera_image.name))
  plt.grid(False)
  plt.axis('off')


def handle_frame(frame):
  for index, image in enumerate(frame.images):
    show_camera_image(image, frame.camera_labels, [3, 3, index+1])


def main():
  FILENAME = '/home/lix16/Data/waymo/training_0000/segment-10017090168044687777_6380_000_6400_000_with_camera_labels.tfrecord'
  dataset = tf.data.TFRecordDataset(FILENAME, compression_type='')
  for data in dataset:
    frame = open_dataset.Frame()
    frame.ParseFromString(bytearray(data.numpy()))
    handle_frame(frame)
    #(range_images, camera_projections, range_image_top_pose) =
    #    frame_utils.parse_range_image_and_camera_projection(frame)
    #plt.show()
    fig.canvas.draw()
    fig.canvas.flush_events()
    #break


if __name__ == '__main__':
  fig = plt.figure(figsize=(25, 20))
  plt.show(block=False)
  main()

