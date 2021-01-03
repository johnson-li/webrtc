import argparse
import os
import numpy as np
import json
import matplotlib.pyplot as plt


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to illustrate the dump folder.')
    parser.add_argument('-p', '--path', default=os.path.expanduser('~/Data/webrtc_exp3/2020-12-03_15-14-41/dump'),
                        help='Dump folder')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    path = args.path
    files = [f for f in os.listdir(path) if f.endswith('.bin')]
    sequences = [int(f.split('.')[0]) for f in files]
    sequences = sorted(sequences)
    first = True
    img = None
    for s in sequences:
        f = os.path.join(path, f'{s}.bin')
        image = np.fromfile(f)
        meta = json.load(open(os.path.join(path, f'{s}.json')))
        width, height = meta['width'], meta['height']
        image = np.frombuffer(image, dtype=np.uint8).reshape((height, width, -1))
        image = image[:, :, :3][:, :, ::-1]
        print(f'Show {f}, resolution: {width}x{height}')
        if not img:
            img = plt.imshow(image)
            plt.show(block=False)
        else:
            img.set_data(image)
        plt.pause(.1)
        plt.draw()


if __name__ == '__main__':
    main()
