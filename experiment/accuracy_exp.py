import argparse
from experiment.config import *
from experiment.base import *
from experiment.logging import logging, get_logger, logging_wrapper
from utils.ssh import paramiko_connect, execute_remote, ftp_pull, ftp_push
import time

LOGGER = logging.getLogger(__name__)
DEV = HOSTS["DEV"]
YOLO_FILES = ['stream.py', 'requirements.txt', 'models.py', 'utils/parse_config.py',
              'utils/utils.py', 'utils/datasets.py', 'utils/augmentations.py',
              'config/yolov3.cfg', 'weights/yolov3.weights', 'data/coco.names']
CLIENT_PYTHON_FILES = ['experiment/fakewebcam.py', 'experiment/client.py',
                       'fakewebcam/pyfakewebcam.py', 'fakewebcam/v4l2.py',
                       'fakewebcam/__init__.py', 'requirements.txt']


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
        ftp_pull(client, client_sftp, '/home/lix16/Workspace/PyTorch-YOLOv3/%s' % (filename,),
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
        ftp_push(client, client_sftp, filename, DATA_YOLO_PATH,
                 REMOTE_YOLO_PATH, executable=False, del_before_push=True)
    for filename in CLIENT_PYTHON_FILES:
        ftp_push(client, client_sftp, filename, PYTHON_SRC_PATH,
                 REMOTE_PYTHON_SRC_PATH, executable=False, del_before_push=True)
    client.close()
    client_sftp.close()


@logging_wrapper(msg='Init Client')
def init_client(logger):
    client = paramiko_connect(DEV)
    client_sftp = paramiko_connect(DEV, ftp=True)
    execute_remote(client, 'bash -c /tmp/webrtc/client_remote_init_wrapper_accuracy_exp.sh')
    client.close()
    client_sftp.close()


@logging_wrapper(msg='Start Client')
def start_client(logger):
    client = paramiko_connect(DEV)
    client_sftp = paramiko_connect(DEV, ftp=True)
    execute_remote(client, 'export server_ip=%s; bash -c /tmp/webrtc/client_remote_accuracy_exp.sh' % DEV['IP'])
    client.close()
    client_sftp.close()


@logging_wrapper(msg='Stop Client')
def stop_client(logger):
    client = paramiko_connect(DEV)
    execute_remote(client, 'killall -s SIGINT peerconnection_client_headless peerconnection_server_headless '
                           'python 2> /dev/null')
    client.close()


def parse_args():
    parser = argparse.ArgumentParser(description='Experiment management tool.')
    parser.add_argument('-s', '--sync', help='Sync data files', action='store_true')
    parser.add_argument('-i', '--init', help='Initiate conda environment', action='store_true')
    parser.add_argument('-r', '--run', help='Run the experiment', action='store_true')
    parser.add_argument('-t', '--stop', help='Stop the experiment after (if) running', action='store_true')
    parser.add_argument('-w', '--wait', type=int, default=0, help='Time in seconds to sleep after running')
    return parser.parse_args()


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
