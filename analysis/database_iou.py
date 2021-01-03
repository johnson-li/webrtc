import numpy as np
import matplotlib.pyplot as plt
from utils.plot import draw_cdf
from utils.metrics.iou import bbox_iou
from analysis.dataset import get_ground_truth

LIMIT = 650


def iou_cls(detections):
    res = []
    for i in range(len(detections)):
        for j in range(i + 1, len(detections)):
            d1 = detections[i]
            d2 = detections[j]
            d1 = (d1['x1'], d1['y1'], d1['x2'], d1['y2'])
            d2 = (d2['x1'], d2['y1'], d2['x2'], d2['y2'])
            res.append(bbox_iou(d1, np.array([d2, ]))[0])
    return res


def iou_statics():
    ground_truth = get_ground_truth(limit=LIMIT)
    ground_truth = {int(k): v for k, v in ground_truth.items()}
    ground_truth = {i: ground_truth[i] for i in range(LIMIT)}
    ious = {}
    for sequence, detections in ground_truth.items():
        cls_list = set([d['cls'] for d in detections])
        for cls in cls_list:
            res = iou_cls(list(filter(lambda x: x['cls'] == cls, detections)))
            ious.setdefault(cls, [])
            ious[cls] += res
    return ious


def illustrate(statics):
    for cls, iou_list in statics.items():
        if iou_list:
            iou_list = sorted(iou_list, reverse=True)
            iou_list = np.array(iou_list)
            draw_cdf(iou_list, f"IOU_{cls}", f'iou_{cls}')
            print(f'cls: {cls}')
            print(len(iou_list[iou_list > 0.2]) / len(iou_list))


def main():
    statics = iou_statics()
    illustrate(statics)


if __name__ == '__main__':
    main()
