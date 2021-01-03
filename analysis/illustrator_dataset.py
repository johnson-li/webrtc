import os
import numpy as np
import argparse
import matplotlib.pyplot as plt

figure = plt.figure(figsize=(9, 6), dpi=60)
ax = figure.gca()
IM = None


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to illustrate the waymo dataset.')
    parser.add_argument('-f', '--folder', help='The folder of the dataset files')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    folder = args.folder
    indexes = []
    for file in os.listdir(folder):
        if file.endswith('.npy'):
            indexes.append(int(file.split('.')[0]))
    indexes = sorted(indexes)
    for index in indexes:
        image = np.load(os.path.join(folder, f'{index}.npy'))
        global IM
        if not IM:
            IM = ax.imshow(image)
            plt.show(block=False)
        else:
            IM.set_data(image)
        plt.title(f'Frame sequence: {index}')
        plt.draw()
        plt.pause(.0001)


if __name__ == '__main__':
    main()
