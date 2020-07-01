import os

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
PROJECT_PATH = os.path.dirname(DIR_PATH)
DATA_PATH = os.path.join(PROJECT_PATH, 'data')
SCRIPTS_PATH = os.path.join(PROJECT_PATH, 'scripts')
RESULTS_PATH = os.path.join(PROJECT_PATH, 'results')
RESOURCE_PATH = os.path.join(PROJECT_PATH, 'resources')
REMOTE_PATH = '/tmp/webrtc'
REMOTE_LOG_PATH = os.path.join(REMOTE_PATH, 'logs')

YOLO_DEV_DIR = '/home/lix16/Workspace/PyTorch-YOLOv3'
DATA_YOLO_PATH = os.path.join(DATA_PATH, 'yolo')
REMOTE_YOLO_PATH = os.path.join(REMOTE_PATH, 'yolo')

YOLOv5_DEV_DIR = '/home/lix16/Workspace/yolov5'
DATA_YOLOv5_PATH = os.path.join(DATA_PATH, 'yolov5')
REMOTE_YOLOV5_PATH = os.path.join(REMOTE_PATH, 'yolov5')

PYTHON_SRC_PATH = os.path.join(PROJECT_PATH, 'python_src')
REMOTE_PYTHON_SRC_PATH = os.path.join(REMOTE_PATH, 'python_src')


