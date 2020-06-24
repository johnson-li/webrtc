import argparse
from experiment.config import *
from experiment.base import *
from experiment.logging import logging, get_logger, logging_wrapper
from utils.ssh import paramiko_connect, execute_remote, ftp_pull, ftp_push

DEV = HOSTS["DEV"]
YOLO_FILES = ['stream.py', 'requirements.txt', 'models.py', 'utils/parse_config.py',
              'utils/utils.py', 'utils/datasets.py', 'utils/augmentations.py',
              'config/yolov3.cfg', 'weights/yolov3.weights', 'data/coco.names']


@logging_wrapper(msg='Prepare Data')
def prepare_data(logger):
    client = paramiko_connect(DEV)
    client_sftp = paramiko_connect(DEV, ftp=True)
    ftp_pull(client, client_sftp,
             '/home/lix16/Workspace/webrtc/src/out/Default/peerconnection_client_headless', DATA_PATH, executable=True)
    ftp_pull(client, client_sftp,
             '/home/lix16/Workspace/webrtc/src/out/Default/peerconnection_server_headless', DATA_PATH, executable=True)
    for filename in YOLO_FILES:
        subdir = '' if filename.rfind('/') == -1 else filename[: filename.rfind('/')]
        ftp_pull(client, client_sftp, '/home/lix16/Workspace/PyTorch-YOLOv3/%s' % (filename, ),
                 os.path.join(DATA_YOLO_PATH, subdir), executable=False)
    client.close()
    client_sftp.close()


@logging_wrapper(msg='Sync Client')
def sync_client(logger):
    client = paramiko_connect(DEV)
    client_sftp = paramiko_connect(DEV, ftp=True)
    execute_remote(client, 'mkdir -p /tmp/webrtc')
    ftp_push(client, client_sftp, 'peerconnection_client_headless', DATA_PATH, REMOTE_PATH, executable=True)
    ftp_push(client, client_sftp, 'peerconnection_server_headless', DATA_PATH, REMOTE_PATH, executable=True)
    ftp_push(client, client_sftp, 'client_remote_accuracy_exp.sh', SCRIPTS_PATH, REMOTE_PATH, executable=True)
    ftp_push(client, client_sftp, 'client_remote_init_accuracy_exp.sh',
             SCRIPTS_PATH, REMOTE_PATH, executable=True, del_before_push=True)
    ftp_push(client, client_sftp, 'client_remote_init_wrapper_accuracy_exp.sh',
             SCRIPTS_PATH, REMOTE_PATH, executable=True, del_before_push=True)
    for filename in YOLO_FILES:
        subdir = '' if filename.rfind('/') == -1 else filename[: filename.rfind('/')]
        ftp_pull(client, client_sftp, '/home/lix16/Workspace/PyTorch-YOLOv3/%s' % filename,
                 os.path.join(DATA_YOLO_PATH, subdir), executable=False)
    client.close()
    client_sftp.close()


@logging_wrapper(msg='Init Client')
def init_client(logger):
    client = paramiko_connect(DEV)
    client_sftp = paramiko_connect(DEV, ftp=True)
    execute_remote(client, 'bash -c /tmp/webrtc/client_remote_init_wrapper_accuracy_exp.sh')
    client.close()
    client_sftp.close()


def parse_args():
    parser = argparse.ArgumentParser(description='Experiment management tool.')
    parser.add_argument('-s', '--sync', help='Sync data files', action='store_true')
    parser.add_argument('-i', '--init', help='Initiate conda environment', action='store_true')
    return parser.parse_args()


def main():
    args = parse_args()
    if args.sync:
        prepare_data()
        sync_client()
    if args.init:
        init_client()


if __name__ == '__main__':
    main()
