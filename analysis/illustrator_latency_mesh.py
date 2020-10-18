import argparse
import json
import os
import matplotlib.pyplot as plt
import numpy as np


def main(metrics):
    args = parse_args()
    path = args.path
    statics = 'med'
    feed = {}
    for p in sorted(os.listdir(path)):
        p = os.path.join(path, p)
        meta = {}
        for line in open(os.path.join(p, 'metadata.txt')).readlines():
            line = line.strip()
            if line:
                line = line.split('=')
                meta[line[0]] = line[1]
        lines = [l.strip() for l in open(os.path.join(p, 'analysis_latency.txt')).readlines()]
        i = lines.index("'===============================STATICS================================'")
        data = lines[i + 1:]
        data = "".join(data)
        data = data.replace("'", '"')
        data = json.loads(data)
        resolution = meta['resolution']
        bitrate = meta['bitrate']
        feed.setdefault(resolution, {})[bitrate] = data[metrics][statics]
    row_values = sorted(feed.keys(), key=lambda x: int(x.split('x')[0]), reverse=True)
    column_values = sorted(list(feed.values())[0], key=lambda x: x)
    data = np.zeros((len(row_values), len(column_values)))
    for i in range(len(row_values)):
        for j in range(len(column_values)):
            data[i][j] = feed[row_values[i]][column_values[j]]
    fig, ax = plt.subplots()
    im = ax.imshow(data)
    ax.set_xticks(np.arange(len(column_values)))
    ax.set_yticks(np.arange(len(row_values)))
    ax.set_xticklabels(column_values)
    ax.set_yticklabels(row_values)
    for i in range(len(row_values)):
        for j in range(len(column_values)):
            text = ax.text(j, i, f'{data[i][j]:.2f}', ha='center', va='center', color='w')
    ax.set_title(f'{statics} {metrics} over different bitrate and resolution')
    fig.tight_layout()
    plt.show()
    plt.savefig(f'heatmap_{statics}_{metrics}.png', dpi=600)


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to visualization in a heatmap.')
    parser.add_argument('-p', '--path', default='/tmp/webrtc/logs', help='Data directory')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    for m in ['decoding_latency2', 'encoding_latency', 'encoded_size (kb)', 'frame_latency', 'frame_transmission_latency', 'packet_latency', 'scheduling_latency']:
        main(m)
