import argparse
import time
from experiment.logging import logging, logging_wrapper
from experiment.main import prepare_data, sync_client, start_server, start_client, stop_client, stop_server
from experiment.base import *
from utils.ssh import paramiko_connect, execute_remote, ftp_pull, ftp_pull_dir, ftp_push, ftp_push_dir
from experiment.config import *

MEC = HOSTS["DEV"]
LOCAL = HOSTS["LOCAL"]


def parse_args():
    parser = argparse.ArgumentParser(
        description='An all in one script to run WebRTC to measure latency and dump received frames.')
    parser.add_argument('-w', '--wait', type=int, default=60, help='Period of a single running case')
    parser.add_argument('-d', '--data-path', default=os.path.expanduser('~/Data/webrtc-exp1'),
                        help='The folder to put the logs')
    args = parser.parse_args()
    return args


@logging_wrapper(msg='Compile server')
def server_compile(bitrate, logger):
    client = paramiko_connect(MEC)
    client_sftp = paramiko_connect(MEC, ftp=True)
    ftp_push(client, client_sftp, 'server_compile.sh', SCRIPTS_PATH, REMOTE_PATH, executable=True)
    execute_remote(client, f'export bitrate={bitrate} ; bash -c {REMOTE_PATH}/server_compile.sh')
    client.close()
    client_sftp.close()


@logging_wrapper(msg='Dump results')
def dump_results(args, resolution, bitrate, logger):
    client = paramiko_connect(MEC)
    client_sftp = paramiko_connect(MEC, ftp=True)
    path = args.data_path
    ftp_pull(client, client_sftp, 'client1.log', REMOTE_LOG_PATH, path)


def conduct_exp(args, resolution, bitrate):
    stop_server(host=MEC)
    stop_client(host=LOCAL)
    server_compile(bitrate)
    time.sleep(1)
    prepare_data(host=MEC)
    sync_client(host=LOCAL)

    start_server(host=MEC)
    time.sleep(3)
    start_client(host=LOCAL, resolution=resolution)
    return
    time.sleep(args.wait)

    stop_server(host=MEC)
    stop_client(host=LOCAL)
    time.sleep(3)

    dump_results(args, resolution, bitrate)


def main():
    args = parse_args()
    bitrate_list = [1000, 2000, 3000, 4000, 5000, 6000]
    resolution_list = ["1000", "2000", "3000", "4000", "5000", "6000"]
    for resolution in resolution_list:
        for bitrate in bitrate_list:
            conduct_exp(args, resolution, bitrate)
            break
        break


if __name__ == '__main__':
    main()
