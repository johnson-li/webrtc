from benchmark.config import *
from pathlib import Path
import os
from uuid import uuid4
import argparse
import time
import json
import socket
from utils2.logging import logging, log_id

logger = logging.getLogger(__name__)


def start_probing_client(target_ip, port, duration, delay, client_id, log_path, pkg_size, direction):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setblocking(0)
        size = max(pkg_size, ID_LENGTH + PACKET_SEQUENCE_BYTES)
        buf = bytearray(size)
        buf[:ID_LENGTH] = client_id.ljust(ID_LENGTH).encode()
        statics = {'probing_received': [], 'probing_sent': [], 'duration': duration, 'lost_modem': 0,
                   'delay': delay, 'pkg_size': pkg_size, 'direction': direction}
        seq = 0
        s.connect((target_ip, port))
        start_ts = time.monotonic()
        last_print = start_ts
        termination_num = 3
        termination_sent = 0
        initial_sent = False
        while True:
            try:
                data, addr = s.recvfrom(1500)
                sequence = int.from_bytes(data[ID_LENGTH: ID_LENGTH + PACKET_SEQUENCE_BYTES], BYTE_ORDER)
                statics['probing_received'].append((time.monotonic(), sequence, len(data)))
            except BlockingIOError as e:
                pass
            now = time.monotonic()
            if now - last_print > 5:
                logger.info(f'{int(now - start_ts)} s has passed')
                last_print = now
            if now - start_ts > duration + termination_sent:
                try:
                    s.send('T'.encode())
                    termination_sent += 1
                except BlockingIOError as e:
                    pass
            else:
                if not initial_sent:
                    try:
                        initial_sent = True
                        s.send(buf)
                    except BlockingIOError as e:
                        print(e)
                if direction in ['pour', 'multi'] and now - (seq * delay / 1000 + start_ts) >= -.001 and now - start_ts <= duration:
                    buf[ID_LENGTH: ID_LENGTH + PACKET_SEQUENCE_BYTES] = seq.to_bytes(PACKET_SEQUENCE_BYTES, BYTE_ORDER)
                    try:
                        s.send(buf)
                        statics['probing_sent'].append([now, seq, len(buf)])
                        seq += 1
                    except BlockingIOError as e:
                        statics['lost_modem'] += 1
                        # statics['probing_sent'].append([now, seq, -1])
            if termination_num == termination_sent:
                logger.info(f'Probing finished')
                path = os.path.join(log_path, f'probing_client_{client_id}.log')
                with open(path, 'w+') as f:
                    json.dump(statics, f)
                    logger.info(f'Dump statics data to {path}')
                    break


def start_control_client(target_ip, port, service, client_id, delay, pkg_size, direction):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((target_ip, port))
        if service == 'probing':
            s.send(json.dumps({'id': client_id,
                               'request': {'type': 'probing', 'delay': delay,
                                           'pkg_size': pkg_size, 'direction': direction}}).encode())
        else:
            logger.info(f'Unsupported service: {service}')
            return
        data = s.recv(1500)
        data = json.loads(data.decode())
        logger.info(f'Received from server: {data}')
        return data


def start_statics_client(target_ip, port, client_id, log_path):
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((target_ip, port))
            s.send(json.dumps({'id': client_id, 'request': {'type': 'statics'}}).encode())
            data = s.recv(1500)
            if data:
                data = json.loads(data.decode())
                logger.info(f'Received from server: {data}')
                if data['status'] == 1:
                    cmd = f'scp mobix:{data["path"]} {log_path}'
                    logger.info(f'cmd: {cmd}')
                    os.system(cmd)
                    break
            time.sleep(.3)


def parse_args():
    parser = argparse.ArgumentParser(description='A UDP client to flood the server')
    parser.add_argument('-s', '--server', default='127.0.0.1', help='The IP address of the benchmark server')
    parser.add_argument('-p', '--port', default=DEFAULT_TCP_CONTROL_PORT, type=int,
                        help='The port of the benchmark server')
    parser.add_argument('-d', '--data-rate', default=DEFAULT_DATA_RATE, type=int,
                        help='The client\'s data rate of sending packets')
    parser.add_argument('-a', '--packet-size', default=1400, type=int,
                        help='The payload size of the UDP packets')
    parser.add_argument('-i', '--direction', choices=['sink', 'pour', 'multi'],
                        default='multi', help='The direction of data flow')
    parser.add_argument('-t', '--duration', default=15, type=int, help='The duration of running the data protocol')
    parser.add_argument('-r', '--probing-delay', default=10, type=float,
                        help='The interval of sending continuous probing packets, in milliseconds')
    parser.add_argument('-l', '--logger', default='/tmp/webrtc/logs', help='The path of statics log')
    parser.add_argument('-b', '--service', choices=['udp_sink', 'udp_pour', 'probing'], default='udp_sink',
                        help='Specify the type of service')
    parser.add_argument('-f', '--fps', default=0, type=int, help='FPS')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    Path(args.logger).mkdir(parents=True, exist_ok=True)
    client_id = str(log_id())
    data = start_control_client(args.server, args.port, args.service,
                                client_id, args.probing_delay, args.packet_size, args.direction)
    if data['status'] == 1 and data['id'] == client_id:
        logger.info(f'Found target service, type: {data["type"]}, '
                    f'protocol: {data.get("protocol", None)}, port: {data.get("port", None)}')
        if data['type'] == 'probing':
            start_probing_client(args.server, data['port'], args.duration, args.probing_delay, client_id, args.logger,
                                 args.packet_size, args.direction)
        start_statics_client(args.server, args.port, client_id, args.logger)
    else:
        logger.error(f"Server error: {data['message']}")


if __name__ == '__main__':
    main()
