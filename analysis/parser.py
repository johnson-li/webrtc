import os
from sklearn.linear_model import LinearRegression
import json
from experiment.logging import logging_wrapper


def on_data(detections, detc, sequences=None):
    det = detc['detection']
    frame_sequence = int(detc['frame_sequence'])
    if sequences and frame_sequence not in sequences:
        return
    detections.setdefault(frame_sequence, {'frame_timestamp': detc['frame_timestamp']})
    detections[frame_sequence].setdefault('detection', [])
    detections[frame_sequence]['detection'].append({'timestamp': detc['yolo_timestamp'],
                                                    'box': [det['x1'], det['y1'], det['x2'],
                                                            det['y2']],
                                                    'class': det['cls_pred'],
                                                    'class_name': det['cls_pred_name'],
                                                    'conf': det['conf'],
                                                    'class_conf': det['cls_conf']})


def post_process(frames):
    for k, v in frames.items():
        if 'packets' in v:
            v['encoded_size'] = sum([p.get('size', 0) for p in v['packets']])
            send_time_stamps = [p['send_timestamp'] for p in v['packets'] if 'send_timestamp' in p]
            if send_time_stamps:
                v['frame_sending_latency'] = max(send_time_stamps) - min(send_time_stamps)


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


def parse_line(line):
    line = line.strip()
    ans = {}
    if '): [LOGITEM ' in line:
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
            try:
                parsed = parse_line(line)
                if parsed:
                    data.append(parsed)
            except Exception as e:
                pass
    return data


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
    if sequence in frames['packet_sequence_index']:
        frame_id, packet = frames['packet_sequence_index'][sequence]
        return packet, frames[frame_id]
    return None, None


def find_packet_by_frame_sequence(frames, sequence):
    if sequence < 0:
        return None
    for frame_id, frame in frames.items():
        for p in frame.get('packets', []):
            if p['frame_sequence'] == sequence:
                return p
    return None


def parse_receiver(frames, path, reg: LinearRegression):
    parsed = parse_logger(path)
    for log_item in parsed:
        try:
            timestamp = reg.predict([[log_item['params'][0][1] / 1000, ], ])[0] * 1000
            item = log_item['item']
            if item == 'DemuxPacket':
                sequence = log_item['params'][1][1]
                frame_sequence = log_item['params'][3][1]
                size = log_item['params'][4][1]
                packet, frame = find_packet(frames, sequence)
                if packet:
                    packet['frame_sequence'] = frame_sequence
                    packet['receive_timestamp'] = timestamp
                    packet['size'] = size
                    frame['frame_sequence'] = frame_sequence
            elif item == 'OnAssembledFrame':
                start_sequence = log_item['params'][1][1]
                frame = find_frame(frames, sequence=start_sequence)
                if frame:
                    frame['assembled_timestamp'] = timestamp
            elif item == 'FrameDecoded':
                frame_sequence = log_item['params'][2][1]
                if frame_sequence > 0 and frame_sequence != 666666 and frame_sequence in frames['frame_sequence_index']:
                    frame = frames[frames['frame_sequence_index'][frame_sequence]]
                    frame['decoded_timestamp'] = timestamp
            elif item == 'ReadyToDecodeFrame':
                frame_sequence = log_item['params'][1][1]
                if frame_sequence > 0 and frame_sequence != 666666 and frame_sequence in frames['frame_sequence_index']:
                    frame = frames[frames['frame_sequence_index'][frame_sequence]]
                    frame['pre_decode_timestamp'] = timestamp
            elif item == 'FrameCompleted':
                frame_sequence = log_item['params'][1][1]
                if frame_sequence > 0 and frame_sequence != 666666 and frame_sequence in frames['frame_sequence_index']:
                    frame = frames[frames['frame_sequence_index'][frame_sequence]]
                    frame['completed_timestamp'] = timestamp
        except Exception as e:
            print(log_item)
            raise e


def parse_packets(path):
    parsed = parse_logger(path)
    sent = []
    received = []
    for i in parsed:
        item, params = i['item'], i['params']
        if item == 'AsyncUDPSocketRead':
            sent.append({'ts': params[0][1], 'size': params[2][1]})
        elif item == 'PhysicalSocketSend':
            received.append({'ts': params[0][1], 'size': params[1][1]})
    return sent, received


def parse_sender(path):
    parsed = parse_logger(path)
    frame_sequence_index = {}
    packet_sequence_index = {}
    frames = {'frame_sequence_index': frame_sequence_index, 'packet_sequence_index': packet_sequence_index}
    for log_item in parsed:
        timestamp = log_item['params'][0][1]
        item = log_item['item']
        if item == 'CreateVideoFrame':
            frame_id = log_item['params'][2][1]
            frame_seq = log_item['params'][3][1]
            frames[frame_id] = {'id': frame_id, 'sequence': frame_seq}
            frame_sequence_index[frame_seq] = frame_id
        # elif item == 'EncoderQueueEnqueue':
        #     frame_id = log_item['params'][2][1]
        #     if frame_id not in frames:
        #         continue
        #     frames[frame_id]['ntp'] = log_item['params'][4][1]
        elif item == 'CreateEncodedImage':
            frame_seq = log_item['params'][5][1]
            if frame_seq not in frame_sequence_index:
                continue
            frame = frames[frame_sequence_index[frame_seq]]
            if frame:
                frame['encoded_time'] = timestamp
                frame['encoded_size'] = log_item['params'][6][1]
                frame['frame_width'] = log_item['params'][7][1]
                frame['frame_height'] = log_item['params'][8][1]
        elif item == 'Packetizer':
            frame_id = log_item['params'][1][1] * 1000
            if frame_id not in frames:
                continue
            frames[frame_id].setdefault('packets', [])
            packet_seq = log_item['params'][2][1]
            rtp_seq = log_item['params'][3][1]
            packet = {'index': packet_seq, 'sequence': rtp_seq}
            frames['packet_sequence_index'][rtp_seq] = (frame_id, packet)
            frames[frame_id]['packets'].append(packet)
        elif item == 'SendPacketToNetwork':
            rtp_seq = log_item['params'][1][1]
            packet, _ = find_packet(frames, rtp_seq)
            if packet:
                packet['send_timestamp'] = timestamp
        # elif item == 'UdpSend':
        #     # TODO: This part does not work for now.
        #     sequence = log_item['params'][1][1]
        #     size = log_item['params'][2][1]
        #     packet, _ = find_packet(frames, sequence)
        #     if packet:
        #         packet['udp_send_time'] = timestamp
        #         packet['udp_size'] = size
        elif item == 'ReadyToCreateEncodedImage':
            frame_id = log_item['params'][1][1]
            if frame_id in frames:
                frames[frame_id]['pre_encode_time'] = timestamp
    return frames


@logging_wrapper(msg='Parse Results [Inference latency]')
def parse_inference_latency(path, logger=None):
    with open(path) as f:
        data = []
        for line in f.readlines():
            line = line.strip()
            if line:
                latency = line.split(' ')[2]
                latency = float(latency)
                data.append(latency)
        return data


@logging_wrapper(msg='Parse Results [Latency]')
def parse_results_latency(result_path, reg: LinearRegression, logger=None):
    client_log1 = os.path.join(result_path, 'client1.log')
    client_log2 = os.path.join(result_path, 'client2.log')
    stream_log = os.path.join(result_path, 'stream.log')
    frames = parse_sender(client_log2)
    parse_receiver(frames, client_log1, reg)
    post_process(frames)
    # parse_stream(frames, stream_log)
    return frames


@logging_wrapper(msg='Parse Results [Accuracy]')
def parse_results_accuracy(result_path, weight=None, sequences=None, logger=None, refresh=False):
    # detections_path = os.path.join(result_path, f'detections.{weight}.json')
    # if os.path.isfile(detections_path) and os.path.getsize(detections_path) > 0 and not refresh:
    #     try:
    #         data = json.load(open(detections_path))
    #         data = {int(k): v for k, v in data.items()}
    #         return data
    #     except Exception as e:
    #         print(f'Failed to parse json file: {detections_path}')
    # detection_log = os.path.join(result_path, 'detections.log')
    dump_dir = os.path.join(result_path, 'dump')
    detections = {}
    # if os.path.isfile(detection_log):
    #     buffer = ''
    #     with open(detection_log, 'r') as f:
    #         for line in f.readlines():
    #             line = line.strip()
    #             buffer += line
    #             if buffer:
    #                 try:
    #                     detc = json.loads(buffer)
    #                 except json.decoder.JSONDecodeError as e:
    #                     continue
    #                 buffer = ''
    #             on_data(detections, detc, sequences)
    if os.path.isdir(dump_dir):
        for path in os.listdir(dump_dir):
            if path.endswith(f'{weight}.txt'):
                with open(os.path.join(dump_dir, path), 'r') as f:
                    for line in f.readlines():
                        line = line.strip()
                        if line:
                            detc = json.loads(line)
                            if detc:
                                on_data(detections, detc, sequences)
    else:
        for path in os.listdir(result_path):
            if path.endswith(f'{weight}.txt') and not path.startswith('analysis'):
                with open(os.path.join(result_path, path), 'r') as f:
                    for line in f.readlines():
                        line = line.strip()
                        if line:
                            detc = json.loads(line)
                            on_data(detections, detc, sequences)
    return detections


def parse_latency_statics(path):
    buffer = ''
    lines = open(f"{path}/analysis_latency..txt").readlines()
    start = False
    for line in lines:
        line = line.strip()
        if line:
            if line.startswith("'======"):
                start = True
                continue
            if start:
                buffer += line
    buffer = buffer.replace("'", '"')
    data = json.loads(buffer)
    return data
