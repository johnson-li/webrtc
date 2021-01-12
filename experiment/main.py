import time
import argparse
from experiment.base import *
from experiment.config import *
from experiment.logging import logging, logging_wrapper
from utils.ssh import paramiko_connect, execute_remote, ftp_pull, ftp_pull_dir, ftp_push, ftp_push_dir

MEC = HOSTS["DEV"]
MOBIX = HOSTS["MOBIX"]
UPF = HOSTS["UPF"]
UE = HOSTS["UE"]
DEV = HOSTS["DEV"]
LOCAL = HOSTS["LOCAL"]
LOGGER = logging.getLogger(__name__)
YOLOv5_FILES = ['stream.py', 'requirements.txt', 'utils/__init__.py', 'utils/datasets.py', 'utils/utils.py',
                'utils/google_utils.py', 'utils/torch_utils.py', 'models/yolo.py', 'models/__init__.py',
                'models/yolov5s.yaml', 'models/experimental.py', 'models/common.py',
                'weights/yolov5s.pt']
CLIENT_PYTHON_FILES = ['experiment/fakewebcam.py', 'experiment/client.py', 'experiment/waymo.py',
                       'experiment/dataset.py', 'experiment/bdd.py',
                       'fakewebcam/pyfakewebcam.py', 'fakewebcam/v4l2.py',
                       'fakewebcam/__init__.py', 'requirements.txt']


@logging_wrapper(msg='Prepare Data')
def prepare_data(logger, host=DEV, ):
    client = paramiko_connect(host)
    client_sftp = paramiko_connect(host, ftp=True)
    ftp_pull(client, client_sftp, '/home/lix16/Workspace/webrtc/src/out/Default/peerconnection_client_headless',
             DATA_PATH, executable=True)
    ftp_pull(client, client_sftp, '/home/lix16/Workspace/webrtc/src/out/Default/peerconnection_server_headless',
             DATA_PATH, executable=True)
    ftp_pull(client, client_sftp, '/home/lix16/Workspace/webrtc/src/out/Default/sync_client', DATA_PATH,
             executable=True)
    ftp_pull(client, client_sftp, '/home/lix16/Workspace/webrtc/src/out/Default/sync_server', DATA_PATH,
             executable=True)
    ftp_pull(client, client_sftp,
             '/home/lix16/Workspace/NetworkMonitor/build/NetworkMonitor', DATA_PATH, executable=True)
    ftp_pull_dir(client, client_sftp, YOLOv5_DEV_DIR, DATA_YOLOv5_PATH, YOLOv5_FILES)
    client.close()
    client_sftp.close()


@logging_wrapper(msg='Sync Server')
def sync_server(logger, host=MEC):
    client = paramiko_connect(host)
    client_sftp = paramiko_connect(host, ftp=True)
    execute_remote(client, 'mkdir -p %s' % (REMOTE_PATH, ))
    execute_remote(client, 'mkdir -p %s' % (REMOTE_YOLOV5_PATH, ))
    ftp_push(client, client_sftp, 'peerconnection_server_headless', DATA_PATH, REMOTE_PATH, executable=True,
             del_before_push=True)
    ftp_push(client, client_sftp, 'peerconnection_client_headless', DATA_PATH, REMOTE_PATH, executable=True,
             del_before_push=True)
    ftp_push(client, client_sftp, 'NetworkMonitor', DATA_PATH, REMOTE_PATH, executable=True)
    ftp_push(client, client_sftp, 'sync_server', DATA_PATH, REMOTE_PATH, executable=True, del_before_push=True)
    ftp_push(client, client_sftp, 'server_remote.sh', SCRIPTS_PATH, REMOTE_PATH, executable=True, del_before_push=True)
    ftp_push(client, client_sftp, 'server_remote_init.sh', SCRIPTS_PATH, REMOTE_PATH, executable=True,
             del_before_push=True)
    ftp_push(client, client_sftp, 'server_remote_init_wrapper.sh', SCRIPTS_PATH, REMOTE_PATH, executable=True,
             del_before_push=True)
    ftp_push_dir(client, client_sftp, DATA_YOLOv5_PATH, REMOTE_YOLOV5_PATH, YOLOv5_FILES)
    client.close()
    client_sftp.close()


@logging_wrapper(msg='Start Server')
def start_server(logger, host=MEC):
    client = paramiko_connect(host)
    client_sftp = paramiko_connect(host, ftp=True)
    execute_remote(client, 'bash -c /tmp/webrtc/server_remote.sh')
    client.close()
    client_sftp.close()


@logging_wrapper(msg='Stop Server')
def stop_server(logger, host=MEC):
    client = paramiko_connect(host)
    execute_remote(client, 'killall -s SIGINT peerconnection_client_headless 2> /dev/null')
    execute_remote(client, 'killall -s SIGINT peerconnection_server_headless 2> /dev/null')
    execute_remote(client, 'killall -s SIGINT sync_server 2> /dev/null')
    execute_remote(client, 'killall -s SIGINT python 2> /dev/null')
    execute_remote(client, 'sudo killall -s SIGINT NetworkMonitor 2> /dev/null')
    client.close()


@logging_wrapper(msg='Sync Client')
def sync_client(logger, host=UE):
    client = paramiko_connect(host)
    client_sftp = paramiko_connect(host, ftp=True)
    execute_remote(client, 'mkdir -p /tmp/webrtc')
    ftp_push(client, client_sftp, 'peerconnection_client_headless', DATA_PATH, REMOTE_PATH, executable=True)
    ftp_push(client, client_sftp, 'sync_client', DATA_PATH, REMOTE_PATH, executable=True)
    ftp_push(client, client_sftp, 'NetworkMonitor', DATA_PATH, REMOTE_PATH, executable=True)
    ftp_push(client, client_sftp, 'client_remote.sh', SCRIPTS_PATH, REMOTE_PATH, executable=True)
    ftp_push(client, client_sftp, 'client_remote_init_wrapper.sh', SCRIPTS_PATH, REMOTE_PATH, executable=True,
             del_before_push=True)
    ftp_push(client, client_sftp, 'client_remote_init.sh', SCRIPTS_PATH, REMOTE_PATH, executable=True,
             del_before_push=True)
    ftp_push_dir(client, client_sftp, PYTHON_SRC_PATH, REMOTE_PYTHON_SRC_PATH, CLIENT_PYTHON_FILES)
    client.close()
    client_sftp.close()


@logging_wrapper(msg='Start Client')
def start_client(logger, host=UE, mec=MEC, resolution='1920x1280'):
    client = paramiko_connect(host)
    client_sftp = paramiko_connect(host, ftp=True)
    execute_remote(client, f'export server_ip={mec["IP"]}; export resolution={resolution}; '
                           f'bash -c /tmp/webrtc/client_remote.sh')
    client.close()
    client_sftp.close()


@logging_wrapper(msg='Stop Client')
def stop_client(logger, host=UE):
    client = paramiko_connect(host)
    execute_remote(client, 'killall -s SIGINT peerconnection_client_headless 2> /dev/null')
    execute_remote(client, 'killall -s SIGINT python 2> /dev/null')
    execute_remote(client, 'sudo killall -s SIGINT NetworkMonitor 2> /dev/null')
    client.close()


@logging_wrapper(msg='Init Client')
def init_client(logger, host=UE):
    client = paramiko_connect(host)
    execute_remote(client, 'bash -c /tmp/webrtc/client_remote_init_wrapper.sh')
    client.close()


@logging_wrapper(msg='Init Server')
def init_server(logger, host=MEC):
    client = paramiko_connect(host)
    execute_remote(client, 'bash -c /tmp/webrtc/server_remote_init_wrapper.sh')
    client.close()


def parse_args():
    parser = argparse.ArgumentParser(description='Experiment management tool.')
    parser.add_argument('-s', '--sync', help='Sync data files', action='store_true')
    parser.add_argument('-i', '--init', help='Initiate conda environment', action='store_true')
    parser.add_argument('-r', '--run', help='Run the experiment', action='store_true')
    parser.add_argument('-t', '--stop', help='Stop the experiment after (if) running', action='store_true')
    parser.add_argument('-w', '--wait', type=int, default=0, help='Time in seconds to sleep after running')
    parser.add_argument('-c', '--client-local', action='store_true', help='Run the client in localhost')
    parser.add_argument('-m', '--mec-local', action='store_true', help='Run the MEC in localhost')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    client = LOCAL if args.client_local else UE
    server = LOCAL if args.mec_local else MOBIX
    if args.sync:
        prepare_data()
        sync_client(host=client)
        sync_server(host=server)
    if args.init:
        init_client(host=client)
        init_server(host=server)
    if args.run:
        start_server(host=server)
        time.sleep(5)
        start_client(host=client)
        if args.wait:
            LOGGER.info('Wait %d seconds for experiment' % args.wait)
            time.sleep(args.wait)

    if args.stop:
        stop_server(host=server)
        stop_client(host=client)


if __name__ == '__main__':
    main()
