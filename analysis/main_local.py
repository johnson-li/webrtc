import argparse
import os
from experiment.logging import logging_wrapper, logging
from analysis.main import parse_results_latency, print_results_latency, parse_results_accuracy, print_results_accuracy

LOGGER = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to analyse the experiment result in the localhost.')
    parser.add_argument('-p', '--plot', action='store_true', help='Plot statics')
    parser.add_argument('-d', '--path', default='/tmp/webrtc/logs', help='Plot statics')
    parser.add_argument('-r', '--recursive', action='store_true', help='Weather to process data recursively in subdirs')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    path = args.path
    if args.recursive:
        for p in os.listdir(path):
            if p.endswith('.bak'):
                continue
            p = os.path.join(path, p)
            print(f'Work on {p}')
            frames = parse_results_latency(p, 0)
            print_results_latency(frames, p, args.plot)
    else:
        frames = parse_results_latency(path, 0)
        print_results_latency(frames, path, args.plot)
        detections = parse_results_accuracy(path)
        print_results_accuracy(detections, path)


if __name__ == '__main__':
    main()
