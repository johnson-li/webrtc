import numpy as np
import torch


def bbox_wh_iou(wh1, wh2):
    wh2 = wh2.t()
    w1, h1 = wh1[0], wh1[1]
    w2, h2 = wh2[0], wh2[1]
    inter_area = torch.min(w1, w2) * torch.min(h1, h2)
    union_area = (w1 * h1 + 1e-16) + w2 * h2 - inter_area
    return inter_area / union_area


def bbox_iou(box1, box2, x1y1x2y2=True):
    """
    Returns the IoU of two bounding boxes
    """
    if not x1y1x2y2:
        # Transform from center and width to exact coordinates
        b1_x1, b1_x2 = box1[0] - box1[2] / 2, box1[0] + box1[2] / 2
        b1_y1, b1_y2 = box1[1] - box1[3] / 2, box1[1] + box1[3] / 2
        b2_x1, b2_x2 = box2[:, 0] - box2[:, 2] / 2, box2[:, 0] + box2[:, 2] / 2
        b2_y1, b2_y2 = box2[:, 1] - box2[:, 3] / 2, box2[:, 1] + box2[:, 3] / 2
    else:
        # Get the coordinates of bounding boxes
        b1_x1, b1_y1, b1_x2, b1_y2 = box1[0], box1[1], box1[2], box1[3]
        b2_x1, b2_y1, b2_x2, b2_y2 = box2[:, 0], box2[:, 1], box2[:, 2], box2[:, 3]

    # get the corrdinates of the intersection rectangle
    inter_rect_x1 = np.maximum(b1_x1, b2_x1)
    inter_rect_y1 = np.maximum(b1_y1, b2_y1)
    inter_rect_x2 = np.minimum(b1_x2, b2_x2)
    inter_rect_y2 = np.minimum(b1_y2, b2_y2)
    # Intersection area
    inter_area = np.maximum(inter_rect_x2 - inter_rect_x1 + 1, 0) * np.maximum(inter_rect_y2 - inter_rect_y1 + 1, 0)
    # Union Area
    b1_area = (b1_x2 - b1_x1 + 1) * (b1_y2 - b1_y1 + 1)
    b2_area = (b2_x2 - b2_x1 + 1) * (b2_y2 - b2_y1 + 1)

    iou = inter_area / (b1_area + b2_area - inter_area + 1e-16)

    return iou


def get_batch_statistics(output, targets, iou_threshold):
    """ Compute true positives, predicted scores and predicted labels per sample """
    pred_boxes = output[:, :4]
    pred_scores = output[:, 4]
    pred_labels = output[:, -1]

    true_positives = np.zeros(pred_boxes.shape[0])

    annotations = targets
    target_labels = annotations[:, 0]
    if annotations.shape[0]:
        detected_boxes = []
        target_boxes = annotations[:, 1:]

        for pred_i in range(pred_boxes.shape[0]):
            pred_box = pred_boxes[pred_i]
            pred_label = pred_labels[pred_i]
            # If targets are found break
            if len(detected_boxes) == annotations.shape[0]:
                break

            # Ignore if label is not one of the target labels
            if pred_label not in target_labels:
                continue

            iou_array = bbox_iou(pred_box, target_boxes)
            box_index = iou_array.argmax()
            iou = iou_array[box_index]
            if iou >= iou_threshold and box_index not in detected_boxes:
                true_positives[pred_i] = 1
                detected_boxes += [box_index]
    return true_positives, pred_scores, pred_labels
