import os
import json
import numpy as np
from experiment.logging import logging_wrapper, logging

LOGGER = logging.getLogger(__name__)
LOG_PATH = '/tmp/webrtc/logs'


def main():
    statics = {}
    statics_client = json.load(open(os.path.join(LOG_PATH, 'udp_client.log')))
    statics_server = json.load(open(os.path.join(LOG_PATH, 'udp_server.log')))
    for service in ['udp_sink', 'udp_pour']:
        statics[service] = {}
        cli, ser = statics_client.get(service, []), statics_server.get(service, [])
        if service == 'udp_sink':
            sender, receiver = cli, ser
        else:
            sender, receiver = ser, cli
        for ts, seq, size in sender:
            statics[service][seq] = {'sequence': seq, 'size': size, 'send_ts': ts * 1000}
        for ts, seq, size in receiver:
            if seq in statics[service]:
                statics[service][seq]['recv_ts'] = ts * 1000
                statics[service][seq]['latency'] = statics[service][seq]['recv_ts'] - statics[service][seq]['send_ts']
            else:
                logging.error(f'Seq: {seq} is missing in the sender\'s log')
        if statics[service]:
            dropped_frames = len(list(filter(lambda x: 'recv_ts' not in x, statics[service].values())))
            latencies = np.array([x['latency'] for x in statics[service].values() if 'latency' in x]) - 1820155277
            print(f'[{service}] Number of frames: {len(statics[service])}, dropped frames: {dropped_frames}, '
                  f'latency: [min: {np.min(latencies)}, mean: {np.mean(latencies)}, '
                  f'max: {np.max(latencies)}, median: {np.median(latencies)}]')


if __name__ == '__main__':
    main()
