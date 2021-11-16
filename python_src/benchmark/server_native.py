import os
import time
import json
import socket
from benchmark.config import DEFAULT_TCP_CONTROL_PORT, DEFAULT_UDP_PROBING_PORT, ID_LENGTH, BYTE_ORDER, \
    PACKET_SEQUENCE_BYTES
from pathlib import Path
from multiprocessing import Process, Manager
from utils2.logging import logging

logger = logging.getLogger(__name__)
LOG_PATH = '/tmp/webrtc/logs'
PROBING_CLIENTS = {}
STATICS = {}


def start_control_server(shared):
    logger.info(f'Running control server')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", DEFAULT_TCP_CONTROL_PORT))
        s.listen()
        while True:
            conn, addr = s.accept()
            with conn:
                logger.info(f'Connected by {addr}')
                data = conn.recv(1024)
                if not data:
                    break
                data = json.loads(data.decode())
                logger.info(f'Received from client: {data}')
                client_id = data['id']
                request = data['request']
                request_type = request.get('type', None)
                shared['direction'] = request.get('direction', 'multi')
                fps = request.get('fps', 0)
                if request_type == 'probing':
                    shared['delay'] = request['delay']
                    shared['pkg_size'] = request['pkg_size']
                    conn.send(json.dumps({'id': client_id, 'status': 1, 'type': 'probing',
                                          'direction': shared['direction'],
                                          'port': DEFAULT_UDP_PROBING_PORT, 'protocol': 'UDP'}).encode())
                elif request_type == 'statics':
                    f = os.path.join(LOG_PATH, f'probing_server_{client_id}.log')
                    ff = os.path.join(LOG_PATH, f'probing_server_{client_id}.log.finish')
                    if not os.path.exists(ff):
                        conn.send(json.dumps({'id': client_id, 'status': 2, 'type': 'statics',
                                              'message': 'not ready'}).encode())
                    else:
                        # data = json.load(open(f))
                        conn.send(json.dumps({'id': client_id, 'status': 1,
                                              'type': 'statics', 'path': f}).encode())

                else:
                    conn.send(json.dumps({'status': -1, 'message': f'Invalid request type: {request_type}'}).encode())


def start_probing_server(shared):
    logger.info('Running probing server')
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setblocking(0)
        s.bind(('0.0.0.0', DEFAULT_UDP_PROBING_PORT))
        statics = {}
        client_id = None
        addr = None

        while True:
            try:
                data, addr_ = s.recvfrom(1500)
                if addr_:
                    if not addr:
                        addr = addr_
                        pkg_size = shared['pkg_size']
                        print('pkg size', pkg_size)
                        buf = bytearray(pkg_size)
                        delay = shared['delay']
                        client_id = data[:ID_LENGTH].decode().strip()
                        buf[:ID_LENGTH] = client_id.encode()
                        probing_delay = shared['delay']
                        statics = {'probing_sent': [], 'probing_received': [], 'sequence': 0,
                                   'start_ts': time.monotonic(),
                                   'client_id': client_id, 'delay': probing_delay}
                    if len(data) == 1 and data[0] == 'T'.encode()[0]:
                        f = os.path.join(LOG_PATH, f'probing_server_{client_id}.log')
                        ff = os.path.join(LOG_PATH, f'probing_server_{client_id}.log.finish')
                        if not os.path.exists(f):
                            json.dump(statics, open(f, 'w+'))
                        with open(ff, 'w+') as ff:
                            ff.write('1')
                        addr = None
                    if addr and addr == addr_:
                        client_id = data[:ID_LENGTH].decode().strip()
                        sequence = int.from_bytes(data[ID_LENGTH: ID_LENGTH + PACKET_SEQUENCE_BYTES], BYTE_ORDER)
                        statics['probing_received'].append([time.monotonic(), sequence, len(data)])
            except BlockingIOError as e:
                pass
            if addr and hared['direction'] in ['sink', 'multi']:
                now = time.monotonic()
                waits = statics['sequence'] * statics['delay'] / 1000.0 - (now - statics['start_ts'])
                if waits < 0.001:
                    buf[ID_LENGTH: ID_LENGTH + PACKET_SEQUENCE_BYTES] = \
                        statics['sequence'].to_bytes(PACKET_SEQUENCE_BYTES, BYTE_ORDER)
                    try:
                        s.sendto(buf, addr)
                        statics['probing_sent'].append([now, statics['sequence'], len(buf)])
                    except BlockingIOError as e:
                        statics['probing_sent'].append([now, statics['sequence'], -1])
                    statics['sequence'] += 1


def main():
    Path(LOG_PATH).mkdir(parents=True, exist_ok=True)
    with Manager() as manager:
        shared = manager.dict()
        control_process = Process(target=start_control_server, args=(shared,))
        probing_process = Process(target=start_probing_server, args=(shared,))
        control_process.start()
        probing_process.start()
        control_process.join()
        probing_process.join()


if __name__ == '__main__':
    main()
