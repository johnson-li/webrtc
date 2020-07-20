import os
import json
from experiment.logging import logging_wrapper, logging


@logging_wrapper(msg='Parse Results [Accuracy]')
def parse_results_accuracy(result_path, logger=None):
    detection_log = os.path.join(result_path, 'detections.log')
    detections = {}
    with open(detection_log, 'r') as f:
        for line in f.readlines():
            line = line.strip()
            if line:
                print(line)
                detc = json.loads(line)
                det = detc['detection']
                frame_sequence = detc['frame_sequence']
                detections.setdefault(frame_sequence, {'frame_timestamp': detc['frame_timestamp']})
                detections[detc['frame_sequence']].setdefault('detection', [])
                detections[detc['frame_sequence']]['detection'].append({'timestamp': detc['yolo_timestamp'],
                                                                        'box': [det['x1'], det['y1'], det['x2'],
                                                                                det['y2']],
                                                                        'class': det['cls_pred'],
                                                                        'class_name': det['cls_pred_name'],
                                                                        'conf': det['conf'],
                                                                        'class_conf': det['cls_conf']})
    return detections
