import os
from analysis.parser import parse_latency_statics
import matplotlib.pyplot as plt
from utils.plot import init_figure_wide
from utils.base import RESULT_DIAGRAM_PATH

CATEGORIES = ['PCC', 'Manual sending rate', 'No CC']


def parse(path, category, bitrate):
    statics = parse_latency_statics(path)
    statics['bitrate'] = bitrate
    statics['category'] = category
    return statics


def illustrate(data):
    packet_latency = {}
    frame_latency = {}
    for d in data:
        if d['category'] != CATEGORIES[2]:
            continue
        packet_latency[d['bitrate']] = d['packet_latency']
        frame_latency[d['bitrate']] = d['frame_transmission_latency']

    fig, ax, font_size = init_figure_wide(figsize=(7, 3))
    bitrates = sorted(list(packet_latency.keys()))
    # print([packet_latency[bitrate]['med'] for bitrate in bitrates])
    # print([frame_latency[bitrate]['med'] for bitrate in bitrates])
    plt.plot([b for b in bitrates], [packet_latency[bitrate]['med'] for bitrate in bitrates], linewidth=2)
    plt.plot([b for b in bitrates], [frame_latency[bitrate]['med'] for bitrate in bitrates], linewidth=2)
    plt.xlabel('Bitrate (Mbps)')
    plt.ylabel('Latency (ms)')
    plt.ylim(0, 42)
    # plt.ylim((13, 40))
    plt.legend(['Packet transmission latency', 'Frame transmission latency'])
    plt.tight_layout(pad=.3)
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'plot_med_packet_latency.pdf'))


def load_network_latency():
    # logs = [('2021:01:13-19:06:55', 1000), ('2021:01:13-19:09:42', 2000), ('2021:01:13-19:12:23', 3000),
    #         ('2021:01:13-19:15:40', 4000)]
    logs = os.listdir(os.path.expanduser('~/Workspace/webrtc-controller/results'))
    logs = list(filter(lambda x: x.startswith('2021:01:14'), logs))
    logs = sorted(logs)
    params = []
    for index, log in enumerate(logs):
        if index >= 30:
            break
        category = CATEGORIES[index // 10]
        bitrate = index % 10 + 1
        params.append(
            (os.path.join(os.path.expanduser('~/Workspace/webrtc-controller/results'), log), category, bitrate))
    data = [parse(*param) for param in params]
    return data


def main():
    data = load_network_latency()
    illustrate(data)


if __name__ == '__main__':
    main()
