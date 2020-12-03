import argparse
import os
from analysis.illustrator_mesh import get_meta
from analysis.frame import handle_frame0, load_caches


def parse_args():
    parser = argparse.ArgumentParser(description='A tool for visualization in a heatmap.')
    parser.add_argument('-p', '--path', default=os.path.expanduser('~/Data/webrtc_exp9'), help='Data directory')
    args = parser.parse_args()
    return args


def handle_frames(path, weight, caches):
    print(path)
    return {}


def main():
    args = parse_args()
    path = args.path
    records = {}
    for d in os.listdir(path):
        d = os.path.join(path, d)
        meta_path = os.path.join(d, 'metadata.txt')
        if not os.path.isfile(meta_path):
            continue
        meta = get_meta(meta_path)
        records.setdefault(meta['resolution'], {})[meta['bitrate']] = d
    resolution = '1680x1120'
    weight = 'yolov5s'
    caches = load_caches()
    for bitrate, path in records[resolution].items():
        res = handle_frames(path, weight, caches)
        print(res)


if __name__ == '__main__':
    main()
