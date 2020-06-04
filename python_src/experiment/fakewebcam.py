import os
import time
import timeit
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import tensorflow as tf
import fakewebcam as webcam
from waymo_open_dataset import dataset_pb2 as open_dataset


DATASET_NUMBERT = 3
FPS = 10


def feed_fake_webcam(images):
  height, width, _ = images[0].shape
  print('Image shape: %dx%d' % (width, height))
  cam = webcam.FakeWebcam('/dev/video1', width, height)
  start_ts = timeit.default_timer()
  for index, image in enumerate(images):
    ts = timeit.default_timer()
    offset_ts = ts - start_ts
    if offset_ts > 1 / FPS * (index + 1):
      print('Frame dropped')
      continue
    elif offset_ts < 1 / FPS * index:
      time.sleep(1 / FPS * index - offset_ts)
      cam.schedule_frame(image)
    else:
      cam.schedule_frame(image)



def patch_images(images):
  return images


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


def main():
  images = []
  counter = 0
  for filename in os.listdir(os.path.expanduser('~/Data/waymo/training_0000')):
    filename = os.path.join(os.path.expanduser('~/Data/waymo/training_0000'), filename)
    print('TF record file: %s' % filename)
    if not filename.endswith('tfrecord'):
      continue
    imgs = load_dataset(filename)
    imgs = patch_images(imgs)
    images += imgs
    counter += 1
    if counter >= DATASET_NUMBERT:
        break
  print('Buffer size: %.2f MB' % (sum([i.size for i in images]) / 1024 / 1024))
  print('Feed fake webcam with %d frames' % (len(images), ))
  feed_fake_webcam(images)


if __name__ == '__main__':
  main()

