import argparse
from experiment.config import *
from experiment.base import *
from experiment.logging import logging, logging_wrapper
from utils.ssh import paramiko_connect, execute_remote, ftp_pull, ftp_push, connect, ftp_pull_dir, ftp_push_dir
import time

LOGGER = logging.getLogger(__name__)
DEV = HOSTS["DEV"]
EXP = HOSTS['DEV']
YOLO_FILES = ['stream.py', 'requirements.txt', 'models.py', 'utils/parse_config.py',
              'utils/utils.py', 'utils/datasets.py', 'utils/augmentations.py',
              'config/yolov3.cfg', 'weights/yolov3.weights', 'data/coco.names']
YOLOv5_FILES = ['stream.py', 'requirements.txt', 'utils/__init__.py', 'utils/datasets.py', 'utils/utils.py',
                'utils/google_utils.py', 'utils/torch_utils.py', 'models/yolo.py', 'models/__init__.py',
                'models/yolov5s.yaml', 'models/experimental.py', 'models/common.py',
                'weights/yolov5s.pt']
CLIENT_PYTHON_FILES = ['experiment/fakewebcam.py', 'experiment/client.py',
                       'fakewebcam/pyfakewebcam.py', 'fakewebcam/v4l2.py',
                       'fakewebcam/__init__.py', 'requirements.txt']


@logging_wrapper(msg='Prepare Data')
def prepare_data(logger):
    client, client_sftp = connect(DEV)
    ftp_pull(client, client_sftp,
             '/home/lix16/Workspace/webrtc/src/out/Default/peerconnection_client_headless', DATA_PATH, executable=True)
    ftp_pull(client, client_sftp,
             '/home/lix16/Workspace/webrtc/src/out/Default/peerconnection_server_headless', DATA_PATH, executable=True)
    ftp_pull(client, client_sftp,
             '/home/lix16/Workspace/webrtc/src/out/Default/sync_client', DATA_PATH, executable=True)
    ftp_pull(client, client_sftp,
             '/home/lix16/Workspace/webrtc/src/out/Default/sync_server', DATA_PATH, executable=True)
    ftp_pull_dir(client, client_sftp, YOLO_DEV_DIR, DATA_YOLO_PATH, YOLO_FILES)
    ftp_pull_dir(client, client_sftp, YOLOv5_DEV_DIR, DATA_YOLOv5_PATH, YOLOv5_FILES)
    client.close()
    client_sftp.close()


@logging_wrapper(msg='Sync Client')
def sync_client(logger):
    client, client_sftp = connect(EXP)
    execute_remote(client, 'mkdir -p /tmp/webrtc')
    ftp_push(client, client_sftp, 'peerconnection_client_headless', DATA_PATH, REMOTE_PATH, executable=True)
    ftp_push(client, client_sftp, 'peerconnection_server_headless', DATA_PATH, REMOTE_PATH, executable=True)
    ftp_push(client, client_sftp, 'client_remote_accuracy_exp.sh', SCRIPTS_PATH, REMOTE_PATH, executable=True)
    ftp_push(client, client_sftp, 'client_remote_init_accuracy_exp.sh',
             SCRIPTS_PATH, REMOTE_PATH, executable=True, del_before_push=True)
    ftp_push(client, client_sftp, 'client_remote_init_wrapper_accuracy_exp.sh',
             SCRIPTS_PATH, REMOTE_PATH, executable=True, del_before_push=True)
    ftp_push(client, client_sftp, 'sync_client', DATA_PATH, REMOTE_PATH, executable=True, del_before_push=True)
    ftp_push(client, client_sftp, 'sync_server', DATA_PATH, REMOTE_PATH, executable=True, del_before_push=True)
    ftp_push_dir(client, client_sftp, DATA_YOLO_PATH, REMOTE_YOLO_PATH, YOLO_FILES)
    ftp_push_dir(client, client_sftp, DATA_YOLOv5_PATH, REMOTE_YOLOV5_PATH, YOLOv5_FILES)
    ftp_push_dir(client, client_sftp, PYTHON_SRC_PATH, REMOTE_PYTHON_SRC_PATH, CLIENT_PYTHON_FILES)
    client.close()
    client_sftp.close()


@logging_wrapper(msg='Init Client')
def init_client(logger):
    client, client_sftp = connect(EXP)
    execute_remote(client, 'bash -c /tmp/webrtc/client_remote_init_wrapper_accuracy_exp.sh')
    client.close()
    client_sftp.close()


@logging_wrapper(msg='Start Client')
def start_client(logger):
    client = paramiko_connect(EXP)
    client_sftp = paramiko_connect(DEV, ftp=True)
    execute_remote(client, 'export server_ip=%s; bash -c /tmp/webrtc/client_remote_accuracy_exp.sh' % DEV['IP'])
    client.close()
    client_sftp.close()


@logging_wrapper(msg='Stop Client')
def stop_client(logger):
    client = paramiko_connect(EXP)
    execute_remote(client, 'killall -s SIGINT peerconnection_client_headless 2> /dev/null')
    execute_remote(client, 'killall -s SIGINT peerconnection_server_headless 2> /dev/null')
    execute_remote(client, 'killall -s SIGINT sync_client 2> /dev/null')
    execute_remote(client, 'killall -s SIGINT sync_server 2> /dev/null')
    execute_remote(client, 'killall -s SIGINT python 2> /dev/null')
    client.close()


def parse_args():
    parser = argparse.ArgumentParser(description='Experiment management tool.')
    parser.add_argument('-s', '--sync', help='Sync data files', action='store_true')
    parser.add_argument('-i', '--init', help='Initiate conda environment', action='store_true')
    parser.add_argument('-r', '--run', help='Run the experiment', action='store_true')
    parser.add_argument('-t', '--stop', help='Stop the experiment after (if) running', action='store_true')
    parser.add_argument('-w', '--wait', type=int, default=0, help='Time in seconds to sleep after running')
    parser.add_argument('-l', '--localhost', action='store_true', help='Conduct the experiment in localhost')
    args = parser.parse_args()
    if args.localhost:
        global EXP
        EXP = HOSTS['LOCAL']
    return args


def main():
    args = parse_args()
    if args.sync:
        prepare_data()
        sync_client()
    if args.init:
        init_client()
    if args.run:
        start_client()
        if args.wait:
            LOGGER.info('Wait %d seconds for experiment' % args.wait)
            time.sleep(args.wait)
    if args.stop:
        stop_client()


if __name__ == '__main__':
    main()
