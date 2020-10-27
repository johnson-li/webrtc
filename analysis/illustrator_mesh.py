import argparse
import json
import os
import matplotlib.pyplot as plt
import numpy as np
from multiprocessing import Pool


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
    data_draw = np.zeros((len(row_values), len(column_values)))
    min_val = 0xffff
    for i in range(len(row_values)):
        for j in range(len(column_values)):
            v = feed.get(row_values[i], {}).get(column_values[j], min_val)
            if 0 < v < min_val:
                min_val = v
    for i in range(len(row_values)):
        for j in range(len(column_values)):
            v = feed.get(row_values[i], {}).get(column_values[j], -1)
            data[i][j] = v
            data_draw[i][j] = max(min_val, v)
    fig, ax = plt.subplots()
    im = ax.imshow(data_draw)
    ax.set_xticks(np.arange(len(column_values)))
    ax.set_yticks(np.arange(len(row_values)))
    ax.set_xticklabels(column_values)
    ax.set_yticklabels(row_values)
    plt.xlabel('Bitrate (Kbps)')
    plt.ylabel('Resolution (width x height)')
    for i in range(len(row_values)):
        for j in range(len(column_values)):
            text = ax.text(j, i, f'{data[i][j]:.2f}' if data[i][j] > 0 else '/', ha='center', va='center', color='w')
    ax.set_title(title)
    fig.tight_layout()
    # plt.show()
    plt.savefig(image_name, dpi=600)


def post_process(val):
    for k, v in val.items():
        for kk, vv in v.items():
            v[kk] = np.median(vv)


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
        bitrate = int(meta['bitrate'])
        if not os.path.isfile(os.path.join(p, f'dump/stream_local{"." if args.weight else ""}{args.weight}.log')):
            print(f'Log is not complete in {p}, resolution: {resolution}, bitrate: {bitrate}')
            if os.path.exists(os.path.join(p, f'dump/stream_local{"." if args.weight else ""}{args.weight}.finish')):
                os.remove(os.path.join(p, f'dump/stream_local{"." if args.weight else ""}{args.weight}.finish'))
            continue
        with open(os.path.join(p, f'dump/stream_local{"." if args.weight else ""}{args.weight}.log')) as f:
            latencies = [inference_latency(l) for l in f.readlines() if l.strip()]
            latencies = list(filter(lambda x: x, latencies))
            latency_feed.setdefault(resolution, {}).setdefault(bitrate, []).append(np.median(latencies))
        with open(os.path.join(p, f'analysis_accuracy{"." if args.weight else ""}{args.weight}.txt')) as f:
            lines = [l.strip() for l in f.readlines()]
            buffer = ''
            for line in lines:
                if line.startswith('{'):
                    buffer = line
                else:
                    buffer += line
            buffer = buffer.replace("'", '"')
            data = json.loads(buffer)
            if data['mAP'] > 0:
                accuracy_feed.setdefault(resolution, {}).setdefault(bitrate, []).append(data['mAP'])
    post_process(accuracy_feed)
    post_process(latency_feed)
    draw_heatmap(accuracy_feed, f'accuracy over different bitrate and resolution [{args.weight}]',
                 f'heatmap_accuracy_{args.weight}.png')
    draw_heatmap(latency_feed, f'inference latency over different bitrate and resolution [{args.weight}]',
                 f'heatmap_inference_latency_{args.weight}.png')


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
        bitrate = int(meta['bitrate'])
        value = data[metrics][statics]
        if value != 'N/A':
            feed.setdefault(resolution, {}).setdefault(bitrate, []).append((float(value)) + (
                bias if metrics in ['frame_latency', 'frame_transmission_latency', 'packet_latency'] else 0))
    post_process(feed)
    draw_heatmap(feed, f'{statics} {metrics} over different bitrate and resolution', f'heatmap_{statics}_{metrics}.png')


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to visualization in a heatmap.')
    parser.add_argument('-p', '--path', default='/tmp/webrtc/logs', help='Data directory')
    parser.add_argument('-w', '--weight', default='', choices=['', 'yolov5s', 'yolov5x'],
                        help='The weight name used in YOLO')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    pool = Pool(12)
    metrics = ['decoding_latency2', 'encoding_latency', 'encoded_size (kb)', 'frame_latency',
               'frame_transmission_latency', 'packet_latency', 'scheduling_latency']
    r = pool.starmap_async(parse_latency, [(args, m) for m in metrics])
    pool.apply_async(parse_accuracy, (args,)).get()
    r.wait()


if __name__ == '__main__':
    main()
