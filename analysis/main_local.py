import argparse
from experiment.logging import logging_wrapper, logging
from analysis.main import parse_results_latency, print_results_latency


LOGGER = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to analyse the experiment result in the localhost.')
    parser.add_argument('-p', '--plot', action='store_true', help='Plot statics')
    parser.add_argument('-d', '--path', default='/tmp/webrtc/logs', help='Plot statics')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    path = args.path
    frames = parse_results_latency(path, 0)
    print_results_latency(frames, path, args.plot)


if __name__ == '__main__':
    main()
