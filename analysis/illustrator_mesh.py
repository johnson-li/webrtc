import argparse
import json
import os
import matplotlib.pyplot as plt
import numpy as np


def get_meta(meta_file):
    meta = {}
    for line in open(os.path.join(meta_file)).readlines():
        line = line.strip()
        if line:
            line = line.split('=')
            meta[line[0]] = line[1]
    return meta


def draw_heatmap(feed, title, image_name):
    row_values = sorted(feed.keys(), key=lambda x: int(x.split('x')[0]), reverse=True)
    column_values = set()
    for l in feed.values():
        for k in l.keys():
            column_values.add(k)
    column_values = sorted(list(column_values))
    data = np.zeros((len(row_values), len(column_values)))
    min_val = 0xffff
    for i in range(len(row_values)):
        for j in range(len(column_values)):
            v = feed.get(row_values[i], {}).get(column_values[j], min_val)
            if 0 < v < min_val:
                min_val = v
    for i in range(len(row_values)):
        for j in range(len(column_values)):
            v = feed.get(row_values[i], {}).get(column_values[j], min_val)
            data[i][j] = max(min_val, v)
    fig, ax = plt.subplots()
    im = ax.imshow(data)
    ax.set_xticks(np.arange(len(column_values)))
    ax.set_yticks(np.arange(len(row_values)))
    ax.set_xticklabels(column_values)
    ax.set_yticklabels(row_values)
    for i in range(len(row_values)):
        for j in range(len(column_values)):
            text = ax.text(j, i, f'{data[i][j]:.2f}', ha='center', va='center', color='w')
    ax.set_title(title)
    fig.tight_layout()
    # plt.show()
    plt.savefig(image_name, dpi=600)


def parse_accuracy(args):
    path = args.path
    accuracy_feed = {}
    latency_feed = {}

    def inference_latency(l):
        l = l.strip()
        return float(l.split(' ')[2])

    for p in sorted(os.listdir(path)):
        if p == 'latest':
            continue
        p = os.path.join(path, p)
        meta = get_meta(os.path.join(p, 'metadata.txt'))
        resolution = meta['resolution']
        bitrate = meta['bitrate']
        if not os.path.isfile(os.path.join(p, 'dump/stream_local.log')):
            print(f'Log is not complete in {p}, resolution: {resolution}, bitrate: {bitrate}')
            if os.path.exists(os.path.join(p, 'dump/stream_local.finish')):
                os.remove(os.path.join(p, 'dump/stream_local.finish'))
            continue
        with open(os.path.join(p, 'dump/stream_local.log')) as f:
            latencies = [inference_latency(l) for l in f.readlines() if l.strip()]
            latencies = list(filter(lambda x: x, latencies))
            latency_feed.setdefault(resolution, {})[bitrate] = np.median(latencies)
        with open(os.path.join(p, 'analysis_accuracy.txt')) as f:
            lines = [l.strip() for l in f.readlines()]
            buffer = ''
            for line in lines:
                if line.startswith('{'):
                    buffer = line
                else:
                    buffer += line
            buffer = buffer.replace("'", '"')
            data = json.loads(buffer)
            accuracy_feed.setdefault(resolution, {})[bitrate] = data['mAP']
    draw_heatmap(accuracy_feed, f'accuracy over different bitrate and resolution', f'heatmap_accuracy.png')
    draw_heatmap(latency_feed, f'inference latency over different bitrate and resolution',
                 f'heatmap_inference_latency.png')


def parse_latency(args, metrics):
    path = args.path
    statics = 'med'
    feed = {}
    for p in sorted(os.listdir(path)):
        if p == 'latest':
            continue
        p = os.path.join(path, p)
        meta = {}
        for line in open(os.path.join(p, 'metadata.txt')).readlines():
            line = line.strip()
            if line:
                line = line.split('=')
                meta[line[0]] = line[1]
        with open(os.path.join(p, 'sync.log')) as f:
            bias = float(f.readlines()[-1].split(' ')[0])
        lines = [l.strip() for l in open(os.path.join(p, 'analysis_latency.txt')).readlines()]
        i = lines.index("'===============================STATICS================================'")
        data = lines[i + 1:]
        data = "".join(data)
        data = data.replace("'", '"')
        data = json.loads(data)
        resolution = meta['resolution']
        bitrate = meta['bitrate']
        value = data[metrics][statics]
        feed.setdefault(resolution, {})[bitrate] = (-1 if value == 'N/A' else float(value)) + (
            bias if metrics in ['frame_latency', 'frame_transmission_latency', 'packet_latency'] else 0)
    draw_heatmap(feed, f'{statics} {metrics} over different bitrate and resolution', f'heatmap_{statics}_{metrics}.png')


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to visualization in a heatmap.')
    parser.add_argument('-p', '--path', default='/tmp/webrtc/logs', help='Data directory')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    for m in ['decoding_latency2', 'encoding_latency', 'encoded_size (kb)', 'frame_latency',
              'frame_transmission_latency', 'packet_latency', 'scheduling_latency']:
        parse_latency(args, m)
    parse_accuracy(args)


if __name__ == '__main__':
    main()
