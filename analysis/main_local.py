import argparse
import os
from experiment.logging import logging_wrapper, logging
from analysis.main import parse_results_latency, print_results_latency, parse_results_accuracy, print_results_accuracy

LOGGER = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to analyse the experiment result in the localhost.')
    parser.add_argument('-p', '--plot', action='store_true', help='Plot statics')
    parser.add_argument('-d', '--path', default='/tmp/webrtc/logs', help='Plot statics')
    parser.add_argument('-w', '--weight', default='yolov5s', help='The weight of YOLO', choices=['yolov5x', 'yolov5s'])
    parser.add_argument('-a', '--accuracy-only', default=False, action='store_true', help='Only parse YOLO logs')
    parser.add_argument('-r', '--recursive', action='store_true', help='Weather to process data recursively in subdirs')
    parser.add_argument('-c', '--compare-with', help='The frame sequences to be validated')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    path = args.path
    sequences = []
    if args.compare_with:
        sequences += [int(f.split('.')[0]) for f in os.listdir(args.compare_with) if f.endswith('.bin')]
    if args.recursive:
        for p in os.listdir(path):
            if p.endswith('.bak'):
                continue
            p = os.path.join(path, p)
            print(f'Work on {p}')
            if not args.accuracy_only:
                frames = parse_results_latency(p, 0)
                print_results_latency(frames, p, args.plot, weight=args.weight)
            detections = parse_results_accuracy(p, weight=args.weight, sequences=sequences)
            print_results_accuracy(detections, p, weight=args.weight)
    else:
        if not args.accuracy_only:
            frames = parse_results_latency(path, 0)
            print_results_latency(frames, path, args.plot, weight=args.weight)
        detections = parse_results_accuracy(path, weight=args.weight, sequences=sequences)
        print_results_accuracy(detections, path, weight=args.weight)


if __name__ == '__main__':
    main()
