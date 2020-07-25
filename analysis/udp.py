import os
import json
import numpy as np
from experiment.logging import logging_wrapper, logging

LOGGER = logging.getLogger(__name__)
LOG_PATH = '/tmp/webrtc/logs'


def main():
    statics = {}
    statics_client = json.load(open(os.path.join(LOG_PATH, 'udp_client.log')))
    statics_server = json.load(open(os.path.join(LOG_PATH, 'udp_client.log')))
    for service in ['udp_sink', 'udp_pour']:
        statics[service] = {}
        cli, ser = statics_client[service], statics_server[service]
        for ts, seq, size in cli:
            statics[service][seq] = {'sequence': seq, 'size': size, 'send_ts': ts}
        for ts, seq, size in ser:
            statics[service][seq]['recv_ts'] = ts
            statics[service][seq]['latency'] = ts - statics[service][seq]['send_ts']
        if statics[service]:
            dropped_frames = len(list(filter(lambda x: 'recv_ts' not in x, statics[service].values())))
            latencies = [x['latency'] for x in statics[service].values()]
            print(f'[{service}] Number of frames: {len(statics[service])}, dropped frames: {dropped_frames}, '
                  f'latency: [min: {np.min(latencies)}, mean: {np.mean(latencies)}, '
                  f'max: {np.max(latencies)}, median: {np.median(latencies)}]')


if __name__ == '__main__':
    main()
