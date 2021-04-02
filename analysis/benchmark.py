import os
import numpy as np
import json
import matplotlib.pyplot as plt
from experiment.base import RESULTS_PATH, DATA_PATH
from utils.base import RESULT_DIAGRAM_PATH

BENCHMARK_PATH = os.path.join(RESULTS_PATH, "benchmark")
SINK_PATH = os.path.join(BENCHMARK_PATH, "sink")
POUR_PATH = os.path.join(BENCHMARK_PATH, "pour")


def parse():
    data = {'sink': {}, 'pour': {}}
    for mode in ['sink', 'pour']:
        path = SINK_PATH if mode == 'sink' else POUR_PATH
        for bitrate in os.listdir(path):
            bitrate = int(bitrate)
            data[mode].setdefault(bitrate, {})
            directory = os.path.join(path, f'{bitrate}')
            client_data = json.load(open(os.path.join(directory, 'udp_client.log'))).get(f'udp_{mode}', [])
            server_data = json.load(open(os.path.join(directory, 'server.log'))).get(f'udp_{mode}', {})
            for d in client_data:
                ts, seq, _ = d
                seq = int(seq)
                data[mode][bitrate].setdefault(seq, {})['client'] = ts
            for seq, v in server_data.items():
                seq = int(seq)
                ts = v['timestamp']
                data[mode][bitrate].setdefault(seq, {})['server'] = ts
    return data


def statics(data):
    result = {}
    bitrates = set()
    for v in data.values():
        for b in v.keys():
            bitrates.add(b)
    bitrates = sorted(bitrates)

    def get_latency(d, mode):
        if mode == 'sink':
            sender = 'client'
            receiver = 'server'
        else:
            sender = 'server'
            receiver = 'client'
        latency_list = []
        for dd in d.values():
            if sender in dd and receiver in dd:
                latency_list.append(dd[receiver] - dd[sender] + 9259492399)
        return np.median(latency_list)

    def get_packet_loss(d, mode):
        return 1 - len(list(filter(lambda x: ('server' if mode == 'sink' else 'client') in x, d.values()))) \
               / len(d.values())

    for mode in data.keys():
        mode_data = data[mode]
        result[mode] = {}
        for bitrate in bitrates:
            bps_data = mode_data[bitrate]
            if not bps_data:
                continue
            result[mode].setdefault(bitrate, {})['latency'] = get_latency(bps_data, mode)
            result[mode].setdefault(bitrate, {})['packet_loss'] = get_packet_loss(bps_data, mode)
    return result


def bps_str(v):
    if v >= 1024 * 1024:
        return f'{int(v / 1024 / 1024)} Mbps'
    if v >= 1024:
        return f'{int(v / 1024)} Kbps'
    return f'{v} bps'


def draw(result):
    for mode in result.keys():
        res = result[mode]
        bitrates = sorted(res.keys())
        plt.figure(figsize=(10, 6))
        plt.plot([bps_str(b) for b in bitrates], [res[b]['packet_loss'] * 100 for b in bitrates])
        plt.title('Packet loss rate (%)')
        plt.xlabel('Bitrate')
        plt.ylabel('Packet loss rate (%)')
        plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'loss_udp_{mode}.png'), dpi=600)
        plt.show()
        plt.figure(figsize=(10, 6))
        plt.plot([bps_str(b) for b in bitrates], [res[b]['latency'] for b in bitrates])
        plt.title('UDP Packet Latency (ms)')
        plt.xlabel('Bitrate')
        plt.ylabel('Packet Transmission Latency (ms)')
        plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'latency_udp_{mode}.png'), dpi=600)
        plt.show()


def main():
    data = parse()
    result = statics(data)
    print(result)
    draw(result)


if __name__ == '__main__':
    main()
