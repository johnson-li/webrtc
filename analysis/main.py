import os
import re
from pprint import pprint
from datetime import datetime
from pathlib import Path
from utils.ssh import paramiko_connect, ftp_pull
from experiment.config import *
from experiment.base import *
from experiment.logging import logging_wrapper


def get_result_path():
    return os.path.join(RESULTS_PATH, datetime.now().strftime("%Y:%m:%d-%H:%M:%S"))


def parse_line(line):
    line = line.strip()
    ans = {}
    if line.startswith('[LOGITEM '):
        i = line.index(']')
        ans['item'] = line[9:i]
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
    frames = {}
    for log_item in parsed:
        timestamp = log_item['params'][0][1]
        item = log_item['item']
        if item == 'CreateVideoFrame':
            frame_id = log_item['params'][2][1]
            frames[frame_id] = {}
        elif item == 'EncoderQueueEnqueue':
            frame_id = log_item['params'][2][1]
            frames[frame_id]['ntp'] = log_item['params'][4][1]
        elif item == 'CreateEncodedImage':
            frame = find_frame(frames, ntp=log_item['params'][2][1])
            if frame:
                if len(log_item['params']) >= 6:
                    frame['encoded_size'] = log_item['params'][5][1]
        elif item == 'Packetizer':
            frame_id = log_item['params'][1][1] * 1000
            frames[frame_id].setdefault('packets', [])
            i = log_item['params'][2][1]
            assert len(frames[frame_id]['packets']) == i
            frames[frame_id]['packets'].append({'index': i, 'sequence': log_item['params'][3][1]})
        elif item == 'SendPacketToNetwork':
            sequence = log_item['params'][1][1]
            success = False
            packet = find_packet(frames, sequence)
            if packet:
                packet['send_timestamp'] = timestamp
        elif item == 'UdpSend':
            # TODO: This part does not work for now.
            sequence = log_item['params'][1][1]
            size = log_item['params'][2][1]
            packet = find_packet(frames, sequence)
            if packet:
                packet['udp_send_time'] = timestamp
                packet['udp_size'] = size
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
        return None
    for frame_id, frame in frames.items():
        for p in frame.get('packets', []):
            if p['sequence'] == sequence:
                return p
    return None


def parse_receiver(frames, path, time_diff):
    parsed = parse_logger(path)
    for log_item in parsed:
        timestamp = log_item['params'][0][1] + time_diff
        item = log_item['item']
        if item == 'DemuxPacket':
            sequence = log_item['params'][1][1]
            rtp_sequence = log_item['params'][2][1]
            packet = find_packet(frames, sequence)
            if packet:
                packet['receive_timestamp'] = timestamp
        elif item == 'OnAssembledFrame':
            start_sequence = log_item['params'][1][1]
            frame = find_frame(frames, sequence=start_sequence)
            frame['assembled_timestamp'] = timestamp


def avg(l):
    if len(l) > 0:
        return sum(l) / len(l)
    return 0


def analyse(frames):
    frame_transmission_times = []
    packet_transmission_times = []
    for frame_id, frame in frames.items():
        if 'assembled_timestamp' in frame.keys():
            frame_transmission_times.append(frame['assembled_timestamp'] - frame_id / 1000)
            for packet in frame['packets']:
                packet_transmission_times.append(packet['receive_timestamp'] - packet['send_timestamp'])
    return {
        'avg_frame_latency (ms)': avg(frame_transmission_times),
        'max_frame_latency (ms)': max(frame_transmission_times),
        'min_frame_latency (ms)': min(frame_transmission_times),
        'avg_packet_latency (ms)': avg(packet_transmission_times),
        'max_packet_latency (ms)': max(packet_transmission_times),
        'min_packet_latency (ms)': min(packet_transmission_times),
    }


@logging_wrapper(msg='Download Results')
def download_results(result_path, logger=None):
    MEC = HOSTS["MEC"]
    client = paramiko_connect(MEC)
    client_sftp = paramiko_connect(MEC, ftp=True)
    ftp_pull(client, client_sftp, os.path.join(REMOTE_LOG_PATH, 'client1.log'), result_path)
    client.close()
    client_sftp.close()

    UE = HOSTS["UE"]
    client = paramiko_connect(UE)
    client_sftp = paramiko_connect(UE, ftp=True)
    ftp_pull(client, client_sftp, os.path.join(REMOTE_LOG_PATH, 'client2.log'), result_path)
    ftp_pull(client, client_sftp, os.path.join(REMOTE_LOG_PATH, 'sync.log'), result_path)
    ftp_pull(client, client_sftp, os.path.join(REMOTE_LOG_PATH, 'detections.log'), result_path)
    client.close()
    client_sftp.close()


def get_time_diff(result_path):
    data = open(os.path.join(result_path, 'sync.log')).read()
    data = data.strip()
    data = data.split('\n')[-1]
    return float(data.split(' ')[0])


@logging_wrapper(msg='Parse Results')
def parse_results(result_path, time_diff, logger=None):
    client_log1 = os.path.join(result_path, 'client1.log')
    client_log2 = os.path.join(result_path, 'client2.log')
    frames = parse_sender(client_log2)
    parse_receiver(frames, client_log1, time_diff)
    return frames


@logging_wrapper(msg='Print Results')
def print_results(frames, result_path, logger=None):
    with open(os.path.join(result_path, 'analysis1.txt'), 'w+') as f:
        for key, value in sorted(frames.items(), key=lambda x: x[0]):
            pprint({key: value}, f)
        statics = analyse(frames)
        pprint(statics, f)


def main():
    path = get_result_path()
    Path(path).mkdir(parents=True, exist_ok=True)
    download_results(path)
    time_diff = get_time_diff(path)
    frames = parse_results(path, time_diff)
    print_results(frames, path)


if __name__ == '__main__':
    main()
