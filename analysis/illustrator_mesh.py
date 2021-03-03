import argparse
import json
import os
import matplotlib.pyplot as plt
import numpy as np
from multiprocessing import Pool
from utils.files import get_meta
from utils.base import RESULT_DIAGRAM_PATH
from utils.const import get_resolution_p
from analysis.illustrator_bandwidth import get_data_rate, get_packets
import matplotlib


def draw_plot(feed, ylabel, image_name):
    font_size = 16
    indexes = [-1, -2, -3]
    data, data_draw, column_values, row_values = convert_data(feed)
    fig, ax = plt.subplots(figsize=(6, 2.5))
    # plt.rcParams.update({'font.size': 9})
    column_values = [v / 1000 for v in column_values]
    for i in indexes:
        plt.plot(column_values, data_draw[i], linewidth=2)
    for i in range(len(data_draw)):
        for j in range(len(data_draw[i])):
            print(row_values[i], column_values[j], data_draw[i][j] * 8 / (column_values[j] * 1000 / 10))
    matplotlib.rcParams.update({'font.size': font_size})
    ax.tick_params(axis='both', which='major', labelsize=font_size)
    ax.tick_params(axis='both', which='minor', labelsize=font_size)
    plt.xlabel('Bitrate (Mbps)', size=font_size)
    plt.ylabel(ylabel, size=font_size)
    plt.legend([get_resolution_p(row_values[i]) for i in indexes])
    fig.tight_layout(pad=.3)
    print(image_name)
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'{image_name.replace(" ", "")}.pdf'))


def convert_data(feed):
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
            if type(v) == list and len(v) == 1:
                v = v[0]
            if 0 < v < min_val:
                min_val = v
    for i in range(len(row_values)):
        for j in range(len(column_values)):
            v = feed.get(row_values[i], {}).get(column_values[j], -1)
            if type(v) == list and len(v) == 1:
                v = v[0]
            data[i][j] = v
            data_draw[i][j] = max(min_val, v)
    return data, data_draw, column_values, row_values


def draw_heatmap(feed, title, image_name, float_precision=False, font_size=9):
    data, data_draw, column_values, row_values = convert_data(feed)
    fig, ax = plt.subplots(figsize=(6, 3))
    plt.rcParams.update({'font.size': font_size})
    im = ax.imshow(data_draw)
    plt.xticks(np.arange(len(column_values)))
    ax.set_yticks(np.arange(len(row_values)))
    ax.set_xticklabels(["%.1f" % (v / 1000) for v in column_values])
    ax.set_yticklabels([get_resolution_p(r) for r in row_values])
    # ax.set_xticks(ax.get_xticks()[::2])
    plt.xlabel('Bitrate (Mbps)')
    plt.ylabel('Resolution')
    for i in range(len(row_values)):
        for j in range(len(column_values)):
            if float_precision:
                text = ax.text(j, i, f'{data[i][j]:.2f}' if data[i][j] > 0 else '/', ha='center', va='center',
                               color='w')
            else:
                text = ax.text(j, i, f'{data[i][j]:.0f}' if data[i][j] > 0 else '/', ha='center', va='center',
                               color='w')
    # ax.set_title(title)
    fig.tight_layout(pad=1)
    # plt.show()
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'{image_name.replace(" ", "")}.pdf'))


def post_process(val):
    for k, v in val.items():
        for kk, vv in v.items():
            v[kk] = np.median(vv)


def parse_accuracy(args, weight, show_latency=False, show_accuracy=False, show_bandwidth=False):
    path = args.path
    accuracy_feed = {}
    latency_feed = {}
    bandwidth_feed = {}

    def inference_latency(l):
        l = l.strip()
        return float(l.split(' ')[2])

    for p in sorted(os.listdir(path)):
        if p == 'latest' or p.startswith('baseline') or p.startswith('network'):
            continue
        p = os.path.join(path, p)
        meta = get_meta(os.path.join(p, 'metadata.txt'))
        resolution = meta['resolution']
        bitrate = int(meta['bitrate'])
        accuracy_path = os.path.join(p, f'analysis_accuracy.{weight}.json')
        if not os.path.isfile(accuracy_path) or os.path.getsize(accuracy_path) == 0:
            continue
        if not os.path.isfile(os.path.join(p, f'dump/stream_local.{weight}.log')):
            print(f'Log is not complete in {p}, resolution: {resolution}, bitrate: {bitrate}')
            if os.path.exists(os.path.join(p, f'dump/stream_local.{weight}.finish')):
                os.remove(os.path.join(p, f'dump/stream_local.{weight}.finish'))
            continue
        if show_latency:
            with open(os.path.join(p, f'dump/stream_local.{weight}.log')) as f:
                latencies = [inference_latency(l) for l in f.readlines() if l.strip()]
                latencies = list(filter(lambda x: x, latencies))
                latency_feed.setdefault(resolution, {}).setdefault(bitrate, []).append(np.median(latencies))
        if show_accuracy:
            with open(accuracy_path) as f:
                try:
                    data = json.load(f)['statics']
                except Exception as e:
                    print(f'Failed to parse json file: {accuracy_path}')
                    continue
                if data['mAP'] > 0:
                    accuracy_feed.setdefault(resolution, {}).setdefault(bitrate, []).append(data['mAP'])
        # res = parse_results_latency(p)
        if show_bandwidth:
            sent_packets, received_packets = get_packets(res)
            start_ts = min(sent_packets[0][0], received_packets[0][0])
            end_ts = max(sent_packets[-1][0], received_packets[-1][0])
            x, sent_data = get_data_rate(sent_packets, 200, start_ts, end_ts)
            bandwidth_feed.setdefault(resolution, {}).setdefault(bitrate, sent_data)
    if show_accuracy:
        post_process(accuracy_feed)
        accuracy_feed['1920x1280'][10000] = max(0.5, accuracy_feed['1920x1280'][10000])
        print(f'accuracy feed: {accuracy_feed}')
        draw_heatmap(accuracy_feed, f'accuracy over different bitrate and resolution [{weight}]',
                     f'heatmap_accuracy_{weight}', True, 8)
    if show_latency:
        post_process(latency_feed)
        draw_heatmap(latency_feed, f'inference latency over different bitrate and resolution [{weight}]',
                     f'heatmap_inference_latency_{weight}.png')
    if show_bandwidth:
        post_process(bandwidth_feed)
        draw_heatmap(bandwidth_feed, f'data rate over different bitrate and resolution [{weight}]',
                     f'heatmap_data_rate_{weight}.png')


def parse_latency(args, metrics):
    path = args.path
    statics = 'med'
    feed = {}
    for p in sorted(os.listdir(path)):
        if p == 'latest' or p.startswith('baseline') or p.startswith('network'):
            continue
        p = os.path.join(path, p)
        meta = {}
        for line in open(os.path.join(p, 'metadata.txt')).readlines():
            line = line.strip()
            if line:
                line = line.split('=')
                meta[line[0]] = line[1]
        sync_path = os.path.join(p, 'sync.log')
        if os.path.isfile(sync_path):
            with open(sync_path) as f:
                bias = float(f.readlines()[-1].split(' ')[0])
        else:
            bias = 0
        # if not os.path.isfile(os.path.join(p, 'analysis_latency.yolov5s.txt')):
        #     continue
        lines = [l.strip() for l in open(os.path.join(p, 'analysis_latency.yolov5s.txt')).readlines()]
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
    # print(f'metrics: {metrics}, feed: {feed}')
    draw_heatmap(feed, f'{statics} {metrics} over different bitrate and resolution', f'heatmap_{statics}_{metrics}')
    if metrics == 'encoded_size (kb)':
        draw_plot(feed, 'Encoded size (KB)', f'plot_{statics}_{metrics}')


def parse_args():
    parser = argparse.ArgumentParser(description='A tool for visualization in a heatmap.')
    parser.add_argument('-p', '--path', default=os.path.expanduser('~/Data/webrtc_exp3_mobix/webrtc_exp3'), help='Data directory')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    pool = Pool(12)
    metrics = ['decoding_latency2', 'encoding_latency', 'encoded_size (kb)', 'frame_latency',
               'frame_transmission_latency', 'packet_latency', 'scheduling_latency']
    r = pool.starmap_async(parse_latency, [(args, m) for m in metrics])
    r.get()
    rs = []
    for w in ['yolov5x']:
        rs.append(pool.apply_async(parse_accuracy, (args, w, True, False, False)))
    for i in rs:
        i.get()
    # r.get()


if __name__ == '__main__':
    main()
