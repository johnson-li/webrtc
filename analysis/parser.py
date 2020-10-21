import os
import json
from experiment.logging import logging_wrapper, logging


def on_data(detections, detc):
    det = detc['detection']
    frame_sequence = int(detc['frame_sequence'])
    detections.setdefault(frame_sequence, {'frame_timestamp': detc['frame_timestamp']})
    detections[frame_sequence].setdefault('detection', [])
    detections[frame_sequence]['detection'].append({'timestamp': detc['yolo_timestamp'],
                                                    'box': [det['x1'], det['y1'], det['x2'],
                                                            det['y2']],
                                                    'class': det['cls_pred'],
                                                    'class_name': det['cls_pred_name'],
                                                    'conf': det['conf'],
                                                    'class_conf': det['cls_conf']})


@logging_wrapper(msg='Parse Results [Accuracy]')
def parse_results_accuracy(result_path, logger=None):
    detection_log = os.path.join(result_path, 'detections.log')
    dump_dir = os.path.join(result_path, 'dump')
    detections = {}
    if os.path.isfile(detection_log):
        buffer = ''
        with open(detection_log, 'r') as f:
            for line in f.readlines():
                line = line.strip()
                buffer += line
                if buffer:
                    try:
                        detc = json.loads(buffer)
                    except json.decoder.JSONDecodeError as e:
                        continue
                    buffer = ''
                on_data(detections, detc)
    elif os.path.isdir(dump_dir):
        for path in os.listdir(dump_dir):
            if path.endswith('txt'):
                with open(os.path.join(dump_dir, path), 'r') as f:
                    for line in f.readlines():
                        line = line.strip()
                        if line:
                            detc = json.loads(line)
                            on_data(detections, detc)

    return detections
