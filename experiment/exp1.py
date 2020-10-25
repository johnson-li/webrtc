import argparse
import time
from shutil import copyfile
from datetime import datetime
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
    ts = datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
    path = os.path.join(path, ts)
    ftp_pull(client, client_sftp, os.path.join(REMOTE_LOG_PATH, 'client1.log'), path)
    ftp_pull(client, client_sftp, os.path.join(REMOTE_LOG_PATH, 'client1.logb'), path)
    ftp_pull(client, client_sftp, os.path.join(REMOTE_LOG_PATH, 'network_server.log'), path)
    ftp_pull_dir(client, client_sftp, os.path.join(REMOTE_LOG_PATH, 'dump'), os.path.join(path, 'dump'))
    copyfile('/tmp/webrtc/logs/client2.log', os.path.join(path, 'client2.log'))
    copyfile('/tmp/webrtc/logs/client2.logb', os.path.join(path, 'client2.logb'))
    copyfile('/tmp/webrtc/logs/sync.log', os.path.join(path, 'sync.log'))
    copyfile('/tmp/webrtc/logs/network_client.log', os.path.join(path, 'network_client.log'))
    with open(os.path.join(path, 'metadata.txt'), 'w+') as f:
        f.write(f'ts={ts}\n')
        f.write(f'resolution={resolution}\n')
        f.write(f'bitrate={bitrate}\n')
        f.write(f'codec=vp8\n')


def conduct_exp(args, resolution, bitrate):
    logging.info(f'Conduct experiment with resolution: {resolution}, bitrate: {bitrate}')
    stop_server(host=MEC)
    stop_client(host=LOCAL)
    server_compile(bitrate)
    time.sleep(1)
    prepare_data(host=MEC)
    sync_client(host=LOCAL)

    start_server(host=MEC)
    time.sleep(3)
    start_client(host=LOCAL, resolution=resolution)
    time.sleep(args.wait)

    stop_server(host=MEC)
    stop_client(host=LOCAL)
    time.sleep(3)

    dump_results(args, resolution, bitrate)


def main():
    args = parse_args()
    bitrate_list = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
    resolution_list = ["480x320", "720x480", "960x640", "1200x800", "1440x960", "1680x1120", "1920x1280"]
    for resolution in resolution_list:
        for bitrate in bitrate_list:
            for i in range(3):
                conduct_exp(args, resolution, bitrate)


if __name__ == '__main__':
    main()
