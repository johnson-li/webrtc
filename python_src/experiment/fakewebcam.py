import os
import time
import timeit
import asyncio
import pathlib
from pathlib import Path
import numpy as np
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import tensorflow as tf
import fakewebcam as webcam
from multiprocessing import Process, Pipe
from waymo_open_dataset import dataset_pb2 as open_dataset


PROJECT_PATH = os.path.dirname(os.path.dirname(pathlib.Path(__file__).parent.absolute()))
print(PROJECT_PATH)
DATASET_NUMBER = 2
FPS = 10
CACHE_PATH = '/tmp/waymo_images'
IMAGE_FILES = ["segment-10017090168044687777_6380_000_6400_000_with_camera_labels.tfrecord", "segment-10023947602400723454_1120_000_1140_000_with_camera_labels.tfrecord",
        "segment-1005081002024129653_5313_150_5333_150_with_camera_labels.tfrecord", "segment-10061305430875486848_1080_000_1100_000_with_camera_labels.tfrecord",
        "segment-10072140764565668044_4060_000_4080_000_with_camera_labels.tfrecord"]


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


def cache_images():
  for filename in IMAGE_FILES:
    filepath = os.path.join(os.path.expanduser('~/Data/waymo/training_0000'), filename)
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
    imgs = load_dataset(filepath)
    for i, img in enumerate(imgs):
        path = os.path.join(cache_dir, '%d.npy' % i)
        np.save(path, img)
    with open(flag_path, 'w') as f:
        f.write('1')


def feed_fake_webcam(cam, index, start_ts, image):
  ts = timeit.default_timer()
  offset_ts = ts - start_ts
  if offset_ts > 1 / FPS * (index + 1):
    print('Frame dropped')
    return
  elif offset_ts < 1 / FPS * index:
    time.sleep(1 / FPS * index - offset_ts)
    cam.schedule_frame(image, index)
  else:
    cam.schedule_frame(image, index)


def fake_webcam(conn):
  cam = webcam.FakeWebcam('/dev/video1', 1920, 1280)
  index = 0
  cache_images()
  print("Images are all cached")
  conn.send(True)
  start_ts = timeit.default_timer()
  for filename in IMAGE_FILES:
    cache_dir = os.path.join(CACHE_PATH, filename)
    for i in range(1000):
      frame_path = os.path.join(cache_dir, '%d.npy' % i)
      print(frame_path)
      if not os.path.isfile(frame_path):
        break
      image = np.load(frame_path)
      feed_fake_webcam(cam, index, start_ts, image)
      index += 1


async def start_udp_server(conn):
  class ServerProtocol:
    def connection_made(self, transport):
      self._transport = transport

    def datagram_received(self, data, addr):
      self._transport.sendto(str(conn.poll()).encode(), addr)

    def connection_lost(self, exc):
      print(exc)

  print("Starting UDP server")
  loop = asyncio.get_running_loop()
  transport, protocol = await loop.create_datagram_endpoint(
      lambda: ServerProtocol(), local_addr=('127.0.0.1', 4401))
  try:
    await asyncio.sleep(3600)  # Serve for 1 hour.
  finally:
    transport.close()


def main():
  parent_conn, child_conn = Pipe()
  process = Process(target=fake_webcam, args=(child_conn, ))
  process.start()
  asyncio.run(start_udp_server(parent_conn))
  process.join()


if __name__ == '__main__':
  main()

