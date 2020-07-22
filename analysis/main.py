import argparse
import shutil
import numpy as np
import matplotlib.pyplot as plt
from pprint import pprint
from datetime import datetime
from pathlib import Path
from utils.ssh import paramiko_connect, ftp_pull
from experiment.config import *
from experiment.base import *
from experiment.logging import logging_wrapper, logging
from analysis.dataset import get_ground_truth, CLASSES, WAYMO_CLASSES
from analysis.parser import parse_results_accuracy
from utils.metrics.iou import get_batch_statistics
from utils.metrics.average_precision import ap_per_class

LOGGER = logging.getLogger(__name__)
WIDTH = 1920
HEIGHT = 1280
IOU_THRESHOLD = .5
OBJECT_SIZE_THRESHOLD = 0
MEC = HOSTS["DEV"]
UE = HOSTS["LOCAL"]
DEV = HOSTS["DEV"]


def get_result_path():
    return os.path.join(RESULTS_PATH, datetime.now().strftime("%Y:%m:%d-%H:%M:%S"))


def parse_line(line):
    line = line.strip()
    ans = {}
    if line.startswith('(stack_trace.h:362): [LOGITEM '):
        i = line.index(']')
        ans['item'] = line[30:i]
        ans['params'] = []
        for item in line[i + 1:].split(','):
            item = item.split(':')
            key = item[0].strip()
            value = item[1].strip()
            if '.' in value:
                try:
                    value = float(value)
                except ValueError as e:
                    pass
            else:
                try:
                    value = int(value)
                except ValueError as e:
                    pass
            if key != 'End':
                ans['params'].append((key, value))
    return ans


def parse_logger(path):
    data = []
    with open(path) as f:
        for line in f.readlines():
            parsed = parse_line(line)
            if parsed:
                data.append(parsed)
    return data


def parse_sender(path):
    parsed = parse_logger(path)
    frame_sequence_index = {}
    frames = {'frame_sequence_index': frame_sequence_index}
    for log_item in parsed:
        timestamp = log_item['params'][0][1]
        item = log_item['item']
        if item == 'CreateVideoFrame':
            frame_id = log_item['params'][2][1]
            frames[frame_id] = {'id': frame_id}
        elif item == 'EncoderQueueEnqueue':
            frame_id = log_item['params'][2][1]
            frames[frame_id]['ntp'] = log_item['params'][4][1]
        elif item == 'CreateEncodedImage':
            frame = find_frame(frames, ntp=log_item['params'][2][1])
            if frame:
                frame['encoded_time'] = timestamp
                frame['frame_sequence'] = log_item['params'][5][1]
                frame_sequence_index[frame['frame_sequence']] = frame['id']
                if len(log_item['params']) >= 7:
                    frame['encoded_size'] = log_item['params'][6][1]
        elif item == 'Packetizer':
            frame_id = log_item['params'][1][1] * 1000
            frames[frame_id].setdefault('packets', [])
            i = log_item['params'][2][1]
            assert len(frames[frame_id]['packets']) == i
            frames[frame_id]['packets'].append({'index': i, 'sequence': log_item['params'][3][1]})
        elif item == 'SendPacketToNetwork':
            sequence = log_item['params'][1][1]
            success = False
            packet, _ = find_packet(frames, sequence)
            if packet:
                packet['send_timestamp'] = timestamp
        elif item == 'UdpSend':
            # TODO: This part does not work for now.
            sequence = log_item['params'][1][1]
            size = log_item['params'][2][1]
            packet, _ = find_packet(frames, sequence)
            if packet:
                packet['udp_send_time'] = timestamp
                packet['udp_size'] = size
        elif item == 'ReadyToCreateEncodedImage':
            frame_id = log_item['params'][1][1]
            frame = frames[frame_id]
            frame['pre_encode_time'] = timestamp
    return frames


def find_frame(frames, sequence=None, ntp=None):
    for frame_id, frame in frames.items():
        if ntp and frame.get('ntp', -2) == ntp:
            return frame
        for p in frame.get('packets', []):
            if sequence and 0 < sequence == p['sequence']:
                return frame
    return None


def find_packet(frames, sequence):
    if sequence < 0:
        return None, None
    for frame_id, frame in frames.items():
        for p in frame.get('packets', []):
            if p['sequence'] == sequence:
                return p, frame
    return None, None


def find_packet_by_frame_sequence(frames, sequence):
    if sequence < 0:
        return None
    for frame_id, frame in frames.items():
        for p in frame.get('packets', []):
            if p['frame_sequence'] == sequence:
                return p
    return None


def parse_receiver(frames, path, time_diff):
    parsed = parse_logger(path)
    for log_item in parsed:
        timestamp = log_item['params'][0][1] + time_diff
        item = log_item['item']
        if item == 'DemuxPacket':
            sequence = log_item['params'][1][1]
            frame_sequence = log_item['params'][2][1]
            packet, frame = find_packet(frames, sequence)
            if packet:
                packet['frame_sequence'] = frame_sequence
                packet['receive_timestamp'] = timestamp
                frame['frame_sequence'] = frame_sequence
        elif item == 'OnAssembledFrame':
            start_sequence = log_item['params'][1][1]
            frame = find_frame(frames, sequence=start_sequence)
            frame['assembled_timestamp'] = timestamp
        elif item == 'FrameDecoded':
            frame_sequence = log_item['params'][2][1]
            if frame_sequence > 0 and frame_sequence != 666666:
                frame = frames[frames['frame_sequence_index'][frame_sequence]]
                frame['decoded_timestamp'] = timestamp


def parse_stream(frames, path):
    with open(path) as f:
        for line in f.readlines():
            if line.startswith('Process image '):
                pass
                # frame = find_packet_by_frame_sequence()
                # frame['yolo_latency'] = 0
            elif line.startswith('New frame is ready'):
                pass
                # frame = find_packet_by_frame_sequence()
                # frame['yolo_latency'] = -1


def avg(l):
    if len(l) > 0:
        return sum(l) / len(l)
    return 0


def median(l):
    if len(l) > 0:
        return np.median(l)
    return 0


def subplot_pdf(data, names, ax):
    if not isinstance(names, list):
        data = np.sort(data)
        p = 1. * np.arange(len(data)) / (len(data) - 1)
        ax.plot(data, p)
        ax.set_xlabel(names)
        ax.set_ylabel('$CDF$')
    else:
        for d, n in zip(data, names):
            d = np.sort(d)
            p = 1. * np.arange(len(d)) / (len(d) - 1)
            ax.plot(d, p)
            ax.set_xlabel('$Latencies\ (ms)$')
            ax.set_ylabel('$CDF$')
        ax.legend(names)


def plot_pdf(data_list, names_list):
    fig = plt.figure(figsize=(16, 9), dpi=200)
    for i in range(len(names_list)):
        ax = fig.add_subplot(1, len(names_list), i + 1)
        subplot_pdf(data_list[i], names_list[i], ax)


def analyse_latency(frames, plot=False):
    packet_transmission_times = []
    frame_transmission_times = []
    frame_encoding_times = []
    frame_pre_encoding_times = []
    frame_decoding_times = []
    transmission_times = []
    assemble_times = []
    for frame_id, frame in frames.items():
        packets = frame.get('packets', None)
        if 'assembled_timestamp' in frame.keys():
            frame_transmission_times.append(frame['assembled_timestamp'] - frame_id / 1000)
            for packet in frame['packets']:
                if 'receive_timestamp' in packet and 'send_timestamp' in packet:
                    packet_transmission_times.append(packet['receive_timestamp'] - packet['send_timestamp'])
        if 'encoded_time' in frame.keys() and 'pre_encode_time' in frame.keys():
            frame_encoding_times.append(frame['encoded_time'] - frame['pre_encode_time'])
        if 'pre_encode_time' in frame.keys():
            frame_pre_encoding_times.append(frame['pre_encode_time'] - frame_id / 1000)
        if 'assembled_timestamp' in frame.keys() and 'packets' in frame.keys():
            assemble_times.append(
                frame['assembled_timestamp'] - max([p.get('receive_timestamp', 0) for p in frame['packets']]))
        if packets:
            transmission_times.append(max([p.get('receive_timestamp', 0) for p in packets]) -
                                      min([p.get('send_timestamp', 999999) for p in packets]))
        if 'decoded_timestamp' in frame:
            frame_decoding_times.append(frame['decoded_timestamp'] - frame['assembled_timestamp'])
    res = {}
    for name, data in [('frame_latency', frame_transmission_times), ('packet_latency', packet_transmission_times)]:
        for opt_name, opt in [('min', min), ('avg', avg), ('max', max), ('median', median)]:
            res['%s_%s (ms)' % (opt_name, name)] = opt(data) if data else 'N/A'
    if plot:
        plot_pdf([[frame_transmission_times, frame_encoding_times, frame_pre_encoding_times, frame_decoding_times,
                   transmission_times, assemble_times],
                  packet_transmission_times],
                 [['$Frame\ latency$', '$Encoding\ latency$', '$Pre\ encoding\ latency$', '$Decoding\ latency$',
                   '$Transmission\ latency$', '$Assemble\ latency$'],
                  '$Packet\ latency\ (ms)$'])
        plt.show()

    return res


def pull(client, client_sftp, filename, local_path, remote_path=REMOTE_LOG_PATH, local=False):
    if local:
        shutil.copyfile(os.path.join(remote_path, filename), os.path.join(local_path, filename))
    else:
        ftp_pull(client, client_sftp, os.path.join(remote_path, filename), local_path)


@logging_wrapper(msg='Download Results')
def download_results(result_path, exp_type, local, logger=None):
    target = MEC if exp_type == 'offloading' else DEV
    client = paramiko_connect(target)
    client_sftp = paramiko_connect(target, ftp=True)
    pull(client, client_sftp, 'client1.log', result_path, local=local)
    pull(client, client_sftp, 'stream.log', result_path, local=local)
    pull(client, client_sftp, 'network_server.log', result_path, local=local)
    client.close()
    client_sftp.close()

    target = UE if exp_type == 'offloading' else DEV
    client = paramiko_connect(target)
    client_sftp = paramiko_connect(target, ftp=True)
    pull(client, client_sftp, 'client2.log', result_path, local=local)
    pull(client, client_sftp, 'sync.log', result_path, local=local)
    pull(client, client_sftp, 'detections.log', result_path, local=local)
    pull(client, client_sftp, 'network_client.log', result_path, local=local)
    client.close()
    client_sftp.close()


def get_time_diff(result_path):
    try:
        data = open(os.path.join(result_path, 'sync.log')).read()
        data = data.strip()
        data = data.split('\n')[-1]
        diff = float(data.split(' ')[0])
        return diff
    except Exception as e:
        return 0


@logging_wrapper(msg='Parse Results [Latency]')
def parse_results_latency(result_path, time_diff, logger=None):
    client_log1 = os.path.join(result_path, 'client1.log')
    client_log2 = os.path.join(result_path, 'client2.log')
    stream_log = os.path.join(result_path, 'stream.log')
    frames = parse_sender(client_log2)
    parse_receiver(frames, client_log1, time_diff)
    # parse_stream(frames, stream_log)
    return frames


def average_precision_coco80(base, predicted):
    outputs = np.array([(*p['box'], p['class_conf'], p['class']) for p in predicted['detection']], dtype=np.float32)
    targets = np.array([(b['cls'], b['x1'], b['y1'], b['x2'], b['y2']) for b in base], dtype=np.float32)
    # print("pre: ", np.sum(outputs[:, -1] == 0))
    # Mapping from coco classes to waymo classes
    # ONLY the vehicle class and the pedestrian class should
    # be considered (https://medium.com/@lattandreas/2d-detection-on-waymo-open-dataset-f111e760d15b)
    # 2,5,6,7 -> 1, step2
    # 0 -> 2, step3
    # 11 -> 3, step4
    # [x] 1,3 -> 4, step1
    # others -> 0, step 5
    if outputs.shape[0]:
        outputs[np.logical_or(outputs[:, -1] == 1, outputs[:, -1] == 3), -1] = 4
        outputs[np.logical_or(outputs[:, -1] == 2,
                              np.logical_or(outputs[:, -1] == 5, np.logical_or(outputs[:, -1] == 6,
                                                                               outputs[:, -1] == 7))), -1] = 1
        outputs[outputs[:, -1] == 0, -1] = 2
        outputs[outputs[:, -1] == 11, -1] = 3
        outputs[outputs[:, -1] >= 4, -1] = 0
        sample_metrics = get_batch_statistics(outputs, targets, iou_threshold=IOU_THRESHOLD)
        return sample_metrics, targets[:, 0]
    return (np.array([]), np.array([]), np.array([])), targets[:, 0] if targets.shape[0] else np.array([])


OBJECT_SIZE = {}


def preprocess(base, predicted):
    res_base, res_predicted = [], []
    for obj in base:
        width = obj['x2'] - obj['x1']
        height = obj['y2'] - obj['y1']
        size = width * height
        OBJECT_SIZE.setdefault(obj['cls'], [])
        OBJECT_SIZE[obj['cls']].append(size)
        if size > OBJECT_SIZE_THRESHOLD and obj['cls'] <= 2:
            res_base.append(obj)
    for obj in predicted['detection']:
        obj['box'][0] *= WIDTH
        obj['box'][2] *= WIDTH
        obj['box'][1] *= HEIGHT
        obj['box'][3] *= HEIGHT
        width = (obj['box'][2] - obj['box'][0])
        height = (obj['box'][3] - obj['box'][1])
        size = width * height
        if size > OBJECT_SIZE_THRESHOLD:
            res_predicted.append(obj)
    predicted['detection'] = res_predicted
    return res_base, predicted


def analyse_accuracy(detections):
    start = min(detections.keys())
    end = max(detections.keys())
    ground_truth = get_ground_truth(start, end)
    true_positives, pred_scores, pred_labels, target_classes = [], [], [], []
    evaluated_frames = []
    frames_of_no_detection = []
    for i in range(start, end + 1):
        if i not in detections or i not in ground_truth:
            # logger.error("The index %d is not in detections or ground truth." % i)
            frames_of_no_detection.append(i)
            continue
        # logger.info("Evaluating frame of sequence: %d" % i)
        evaluated_frames.append(i)
        predicted = detections[i]
        base, predicted = preprocess(ground_truth[i], predicted)
        [tp, ps, pl], tc = average_precision_coco80(base, predicted)
        true_positives += tp.tolist()
        pred_scores += ps.tolist()
        pred_labels += pl.tolist()
        target_classes += tc.tolist()
    precision, recall, AP, f1, ap_class = ap_per_class(np.array(true_positives), np.array(pred_scores),
                                                       np.array(pred_labels), np.array(target_classes))
    return {'AP': AP.tolist(), 'AP Classes': ap_class.tolist(), 'mAP': AP.mean(),
            'Evaluated frames': evaluated_frames, 'Frames of no detection': frames_of_no_detection}


@logging_wrapper(msg='Print Results [Latency]')
def print_results_latency(frames, result_path, plot, logger=None):
    with open(os.path.join(result_path, 'analysis_latency.txt'), 'w+') as f:
        frames.pop('frame_sequence_index')
        for key, value in sorted(frames.items(), key=lambda x: x[0]):
            pprint({key: value}, f)
        statics = analyse_latency(frames, plot=plot)
        pprint(statics, f)


@logging_wrapper(msg='Print Results [Accuracy]')
def print_results_accuracy(detections, result_path, logger=None):
    with open(os.path.join(result_path, 'analysis_accuracy.txt'), 'w+') as f:
        for key, value in sorted(detections.items(), key=lambda x: x[0]):
            pprint({key: value}, f)
        statics = analyse_accuracy(detections)
        pprint(statics, f)
        statics.pop('Evaluated frames')
        statics.pop('Frames of no detection')
        logger.log(statics)


def draw_statics():
    for cls, sizes in OBJECT_SIZE.items():
        sizes = np.array(sizes)
        sizes.sort()
        fig = plt.subplot()
        plt.title('Distribution of %s\'s sizes' % WAYMO_CLASSES[cls])
        print('Middle size of %s: %d' % (WAYMO_CLASSES[cls], sizes[len(sizes) // 2]))
        plt.plot(np.log(sizes), np.cumsum(np.ones(len(sizes))) / len(sizes))
        plt.show()


def parse_args():
    parser = argparse.ArgumentParser(description='A tool to analyse the experiment result.')
    parser.add_argument('-f', '--folder', help='Result folder')
    parser.add_argument('-m', '--min-object', type=int, help='The minimal size of the objects. Smaller ones, both '
                                                             'in the ground truth and the prediction, are ignored.')
    parser.add_argument('-t', '--type', default='offloading', choices=['offloading', 'singleton'],
                        help='The type of the experiment. Offloading: the client runs on the vehicle (UE) and '
                             'the server runs on the edge (MEC). Singleton: both the client '
                             'and the server runs on the same machine (DEV).')
    parser.add_argument('-l', '--local', action='store_true', help='Copy the results from localhost')
    parser.add_argument('-p', '--plot', action='store_true', help='Plot statics')
    args = parser.parse_args()
    if args.min_object is not None:
        global OBJECT_SIZE_THRESHOLD
        OBJECT_SIZE_THRESHOLD = args.min_object
    return args


def main():
    args = parse_args()
    exp_type = args.type
    folder = args.folder
    if not folder:
        path = get_result_path()
        Path(path).mkdir(parents=True, exist_ok=True)
        download_results(path, exp_type, args.local)
    else:
        path = os.path.abspath(folder)
        if not os.path.isdir(path):
            LOGGER.error("The result path is not found")
            exit(-1)
    time_diff = get_time_diff(path)
    LOGGER.info(f'Time diff: {time_diff}')
    try:
        frames = parse_results_latency(path, time_diff)
        print_results_latency(frames, path, args.plot)
        pass
    except TypeError as e:
        LOGGER.error("Fatal error in calculating latency", exc_info=True)
    try:
        detections = parse_results_accuracy(path)
        print_results_accuracy(detections, path)
    except TypeError as e:
        LOGGER.error("Fatal error in calculating accuracy", exc_info=True)

    # draw_statics()


if __name__ == '__main__':
    main()
