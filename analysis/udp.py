import os
import json
import argparse
import numpy as np
from experiment.logging import logging_wrapper, logging

LOGGER = logging.getLogger(__name__)
LOG_PATH = ""


def parse_args():
    parser = argparse.ArgumentParser(description='Analysis the UDP benchmark result')
    parser.add_argument('-p', '--log-path', default='/tmp/webrtc/logs',
                        help='The path where UDP benchmark logs are stored')
    args = parser.parse_args()
    global LOG_PATH
    LOG_PATH = args.log_path
    return args


def main():
    args = parse_args()
    statics = {}
    statics_client = json.load(open(os.path.join(LOG_PATH, 'udp_client.log')))
    statics_server = json.load(open(os.path.join(LOG_PATH, 'udp_server.log')))
    for service in ['udp_sink', 'udp_pour']:
        statics[service] = {}
        reorder_count = 0
        last_ts = 0
        cli, ser = statics_client.get(service, []), statics_server.get(service, [])
        if service == 'udp_sink':
            sender, receiver = cli, ser
        else:
            sender, receiver = ser, cli
        for ts, seq, size in sender:
            statics[service][seq] = {'sequence': seq, 'size': size, 'send_ts': ts * 1000}
        receiver.sort(key=lambda x: x[1])
        for ts, seq, size in receiver:
            if seq in statics[service]:
                statics[service][seq]['recv_ts'] = ts * 1000
                statics[service][seq]['latency'] = statics[service][seq]['recv_ts'] - statics[service][seq]['send_ts']
                last_ts = max(last_ts, ts)
                if ts < last_ts:
                    reorder_count += 1
            else:
                logging.error(f'Seq: {seq} is missing in the sender\'s log')
        if statics[service]:
            dropped_frames = [i['sequence'] for i in list(filter(lambda x: 'recv_ts' not in x, statics[service].values()))]
            print(dropped_frames)
            dropped_frames = len(dropped_frames)
            bias = np.abs(1987964585)
            latencies = np.array([x['latency'] for x in statics[service].values() if
                                  'latency' in x]) + (-bias if service == 'udp_sink' else bias)
            reorder_rate = reorder_count / (len(statics[service]) - dropped_frames)
            print(f'[{service}] Number of frames: {len(statics[service])}, '
                  f'dropped frames: {dropped_frames} ({100 * dropped_frames / len(statics[service]):.2f}%), '
                  f'reordered frames: {reorder_count} ({reorder_rate:.2f}%), '
                  f'latency: [min: {np.min(latencies)}, mean: {np.mean(latencies)}, '
                  f'max: {np.max(latencies)}, median: {np.median(latencies)}]')


if __name__ == '__main__':
    main()
