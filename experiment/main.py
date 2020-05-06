from experiment.config import *
from experiment.base import *
from utils.ssh import paramiko_connect, execute_remote, ftp_pull, ftp_push
import paramiko
import stat
import os
import time
import argparse
from experiment.logging import logging, get_logger, logging_wrapper

MEC = HOSTS["MEC"]
UPF = HOSTS["UPF"]
UE = HOSTS["UE"]
DEV = HOSTS["DEV"]
logger = logging.getLogger(__name__)


@logging_wrapper(msg='Prepare Data')
def prepare_data(logger):
    client = paramiko_connect(DEV)
    client_sftp = paramiko_connect(DEV, ftp=True)
    ftp_pull(client, client_sftp, '/home/lix16/Workspace/webrtc/src/out/Default/peerconnection_client_headless', DATA_PATH, executable=True)
    ftp_pull(client, client_sftp, '/home/lix16/Workspace/webrtc/src/out/Default/peerconnection_server_headless', DATA_PATH, executable=True)
    ftp_pull(client, client_sftp, '/home/lix16/Workspace/webrtc/src/out/Default/sync_client', DATA_PATH, executable=True)
    ftp_pull(client, client_sftp, '/home/lix16/Workspace/webrtc/src/out/Default/sync_server', DATA_PATH, executable=True)
    ftp_pull(client, client_sftp, '/home/lix16/Workspace/darknet/streaming', DATA_PATH, executable=True)
    client.close()
    client_sftp.close()


@logging_wrapper(msg='Sync Server')
def sync_server(logger):
    client = paramiko_connect(MEC)
    client_sftp = paramiko_connect(MEC, ftp=True)
    execute_remote(client, 'mkdir -p %s' % (REMOTE_PATH))
    ftp_push(client, client_sftp, 'peerconnection_server_headless', DATA_PATH, REMOTE_PATH, executable=True, del_before_push=True)
    ftp_push(client, client_sftp, 'peerconnection_client_headless', DATA_PATH, REMOTE_PATH, executable=True, del_before_push=True)
    ftp_push(client, client_sftp, 'sync_server', DATA_PATH, REMOTE_PATH, executable=True, del_before_push=True)
    ftp_push(client, client_sftp, 'streaming', DATA_PATH, REMOTE_PATH, executable=True, del_before_push=True)
    ftp_push(client, client_sftp, 'server_remote.sh', SCRIPTS_PATH, REMOTE_PATH, executable=True, del_before_push=True)
    client.close()
    client_sftp.close()


@logging_wrapper(msg='Start Server')
def start_server(logger):
    client = paramiko_connect(MEC)
    client_sftp = paramiko_connect(MEC, ftp=True)
    execute_remote(client, 'bash -c /tmp/webrtc/server_remote.sh')
    client.close()
    client_sftp.close()


@logging_wrapper(msg='Stop Server')
def stop_server(logger):
    client = paramiko_connect(MEC)
    execute_remote(client, 'killall -s SIGINT peerconnection_client_headless peerconnection_server_headless streaming 2> /dev/null')
    client.close()


@logging_wrapper(msg='Sync Client')
def sync_client(logger):
    client = paramiko_connect(UE)
    client_sftp = paramiko_connect(UE, ftp=True)
    execute_remote(client, 'mkdir -p /tmp/webrtc')
    ftp_push(client, client_sftp, 'peerconnection_client_headless', DATA_PATH, REMOTE_PATH, executable=True)
    ftp_push(client, client_sftp, 'sync_client', DATA_PATH, REMOTE_PATH, executable=True)
    ftp_push(client, client_sftp, 'client_remote.sh', SCRIPTS_PATH, REMOTE_PATH, executable=True)
    client.close()
    client_sftp.close()


@logging_wrapper(msg='Start Client')
def start_client(logger):
    client = paramiko_connect(UE)
    client_sftp = paramiko_connect(UE, ftp=True)
    execute_remote(client, 'export server_ip=%s; bash -c /tmp/webrtc/client_remote.sh' % MEC['IP'])
    client.close()
    client_sftp.close()


@logging_wrapper(msg='Stop Client')
def stop_client(logger):
    client = paramiko_connect(UE)
    execute_remote(client, 'killall -s SIGINT peerconnection_client_headless 2> /dev/null')
    client.close()


def parse_args():
    parser = argparse.ArgumentParser(description='Experiment management tool.')
    parser.add_argument('--sync', help='Sync data files', action='store_true')
    parser.add_argument('--run', help='Run the experiment', action='store_true')
    parser.add_argument('--stop', help='Stop the experiment after (if) running', action='store_true')
    parser.add_argument('--wait', type=int, default=0, help='Time in seconds to sleep after running')
    parser.set_defaults(sync=False)
    parser.set_defaults(run=False)
    parser.set_defaults(stop=False)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.sync:
        prepare_data()
        sync_client()
        sync_server()
    if args.run:
        start_server()
        start_client()
        if args.wait:
            logger.info('Wait %d seconds for experiment' % args.wait)
            time.sleep(args.wait)

    if args.stop:
        stop_server()
        stop_client()


if __name__ == '__main__':
    main()

