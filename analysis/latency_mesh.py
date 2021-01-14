import os
from analysis.parser import parse_latency_statics
import matplotlib.pyplot as plt
from utils.plot import init_figure_wide
from utils.base import RESULT_DIAGRAM_PATH


def parse(path, bitrate):
    statics = parse_latency_statics(path)
    statics['bitrate'] = bitrate
    return statics


def illustrate(data):
    packet_latency = {}
    frame_latency = {}
    for d in data:
        packet_latency[d['bitrate']] = d['packet_latency']
        frame_latency[d['bitrate']] = d['frame_transmission_latency']

    fig, ax, font_size = init_figure_wide(figsize=(8, 3))
    bitrates = sorted(list(packet_latency.keys()))
    print([packet_latency[bitrate]['med'] for bitrate in bitrates])
    print([frame_latency[bitrate]['med'] for bitrate in bitrates])
    plt.plot([b / 1000 for b in bitrates], [packet_latency[bitrate]['med'] for bitrate in bitrates])
    plt.plot([b / 1000 for b in bitrates], [frame_latency[bitrate]['med'] for bitrate in bitrates])
    plt.xlabel('Bitrate (Mbps)')
    plt.ylabel('Latency (ms)')
    plt.ylim((13, 40))
    plt.legend(['Packet transmission latency', 'Frame transmission latency'])
    plt.tight_layout(pad=.3)
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'plot_med_packet_latency.pdf'))


def main():
    logs = [('2021:01:13-19:06:55', 1000), ('2021:01:13-19:09:42', 2000), ('2021:01:13-19:12:23', 3000),
            ('2021:01:13-19:15:40', 4000)]
    logs = [(os.path.join(os.path.expanduser('~/Workspace/webrtc-controller/results'), log[0]), log[1]) for log in logs]
    data = [parse(*log) for log in logs]
    illustrate(data)


if __name__ == '__main__':
    main()
