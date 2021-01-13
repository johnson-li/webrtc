import os
import time
import timeit
import asyncio
import pathlib
import argparse
import fakewebcam as webcam
from multiprocessing import Process, Pipe
from experiment.waymo import WaymoDataSet
from experiment.dataset import DataSet

FPS = 10
DATASET = DataSet()


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
    videos = [f for f in os.listdir('/dev') if f.startswith('video')]
    videos = sorted(videos)
    cam = webcam.FakeWebcam(os.path.join('/dev', videos[-1]), 1920, 1280)
    index = 0
    DATASET.cache_images()
    print("Images are all cached")
    conn.send(True)
    start_ts = timeit.default_timer()
    for image in DATASET.images():
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


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to feed videos from dataset to a v4l2loopback webcam.')
    parser.add_argument('-d', '--dataset', choices=['waymo', 'bdd'], default='waymo', help='the data set to use')
    parser.add_argument('-f', '--fps', type=int, default=10, help='the number of frames per second')
    args = parser.parse_args()
    global DATASET, FPS
    if args.dataset == 'waymo':
        DATASET = WaymoDataSet()
    FPS = args.fps
    return args


def main():
    args = parse_args()
    parent_conn, child_conn = Pipe()
    process = Process(target=fake_webcam, args=(child_conn,))
    process.start()
    asyncio.run(start_udp_server(parent_conn))
    process.join()


if __name__ == '__main__':
    main()
