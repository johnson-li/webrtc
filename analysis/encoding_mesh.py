import os
import argparse


def parse_args():
    parser = argparse.ArgumentParser(description='A tool for visualization in a heatmap.')
    parser.add_argument('-p', '--path', default=os.path.expanduser('~/Data/webrtc_exp3'), help='Data directory')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()


if __name__ == '__main__':
    main()
