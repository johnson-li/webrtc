import os
import argparse
import asyncio
import time
import json
from asyncio import transports

from benchmark import UdpServerProtocol
from benchmark.config import *
from typing import Tuple
from utils2.logging import logging

logger = logging.getLogger(__name__)
STATICS = {}
POUR_CLIENTS = {}


class UdpDataPourServerProtocol(UdpServerProtocol):
    async def pour(self, client_id, buffer):
        info = POUR_CLIENTS[client_id]
        wait = len(buffer) * 8 * info['sequence'] / info['bitrate'] - \
               (time.clock_gettime(time.CLOCK_MONOTONIC) - info['start_ts'])
        if wait > 0:
            await asyncio.sleep(wait)
        buffer[: PACKET_SEQUENCE_BYTES] = info['sequence'].to_bytes(PACKET_SEQUENCE_BYTES, BYTE_ORDER)
        STATICS[client_id]['udp_pour'].append((time.clock_gettime(time.CLOCK_MONOTONIC), info['sequence'], len(buffer)))
        info['sequence'] = info['sequence'] + 1
        self._transport.sendto(buffer, info['addr'])
        if time.clock_gettime(time.CLOCK_MONOTONIC) - info['start_ts'] < info['duration']:
            asyncio.create_task(self.pour(client_id, buffer))
        else:
            self._transport.sendto('T'.encode(), info['addr'])

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        data = json.loads(data.decode())
        client_id = data['id']
        cmd = data['command']
        POUR_CLIENTS[client_id] = {'start_ts': time.clock_gettime(time.CLOCK_MONOTONIC), 'addr': addr}
        if cmd == 'start':
            POUR_CLIENTS[client_id].update({'bitrate': data['bitrate'], 'duration': data['duration'], 'sequence': 0})
            STATICS.setdefault(client_id, {}).setdefault('udp_pour', [])
        asyncio.create_task(self.pour(client_id, bytearray(os.urandom(data['packet_size']))))


class UdpDataSinkServerProtocol(UdpServerProtocol):
    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        client_id = data[:ID_LENGTH].decode('utf-8')
        sequence = int.from_bytes(data[ID_LENGTH:ID_LENGTH + PACKET_SEQUENCE_BYTES], BYTE_ORDER)
        STATICS[client_id]['udp_sink'].append((time.clock_gettime(time.CLOCK_MONOTONIC), sequence, len(data)))


class TcpControlServerProtocol(asyncio.Protocol):

    def __init__(self) -> None:
        self._transport = None

    def connection_made(self, transport: transports.BaseTransport) -> None:
        self._transport = transport
        logger.info(f'Got new connection from {transport}')

    def data_received(self, data: bytes) -> None:
        data = data.decode('utf-8').strip()
        try:
            data = json.loads(data)
            client_id = data['id']
            request = data['request']
            request_type = request['type']
            if request_type == 'udp_sink':
                STATICS.setdefault(client_id, {}).setdefault('udp_sink', [])
                self._transport.write(json.dumps({'id': client_id, 'status': 1, 'type': 'sink', 'protocol': 'UDP',
                                                  'port': DEFAULT_UDP_DATA_SINK_PORT}).encode())
            elif request_type == 'udp_pour':
                self._transport.write(json.dumps({'id': client_id, 'status': 1, 'type': 'pour', 'protocol': 'UDP',
                                                  'port': DEFAULT_UDP_DATA_POUR_PORT}).encode())
            elif request_type == 'udp_echo':
                self._transport.write(json.dumps(data).encode())
            elif request_type == 'statics':
                self._transport.write(json.dumps({'id': client_id, 'status': 1, 'type': 'statics',
                                                  'statics': STATICS[client_id]}).encode())
            else:
                self._transport.write(json.dumps({'status': -1,
                                                  'message': f'Invalid request type: {request_type}'}).encode())
        except (json.decoder.JSONDecodeError, KeyError) as e:
            logger.warning(f'Invalid request: {data}')
            self._transport.write(json.dumps({'status': -1, 'message': 'Malformed request', 'error': str(e)}).encode())


class UdpControlServerProtocol(UdpServerProtocol):
    def on_sink_request(self, request, addr):
        STATICS.setdefault(addr, {}).update({'udp_sink': []})

        self._transport.sendto(json.dumps({'status': 1, 'type': 'sink', 'protocol': 'UDP',
                                           'port': DEFAULT_UDP_DATA_SINK_PORT}).encode(), addr)

    def on_pour_request(self, request, addr):
        self._transport.sendto(json.dumps({'status': 1, 'type': 'sink', 'protocol': 'UDP',
                                           'port': DEFAULT_UDP_DATA_POUR_PORT}).encode(), addr)

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        data = data.decode('utf-8').strip()
        logger.info(f'Received request {data} from {addr[0]}:{addr[1]}')
        try:
            data = json.loads(data)
            request = data['request']
            request_type = request['type']
            if request_type == 'sink':
                self.on_sink_request(request, addr)
            elif request_type == 'pour':
                self.on_pour_request(request, addr)
            elif request_type == 'echo':
                self._transport.sendto(json.dumps(data).encode(), addr)
            else:
                self._transport.sendto(
                    json.dumps({'status': -1, 'message': f'Invalid request type: {request_type}'}).encode(), addr)
        except (json.decoder.JSONDecodeError, KeyError) as e:
            logger.warning(f'Invalid request: {data}')
            self._transport.sendto(json.dumps({'status': -1, 'message': 'Malformed request',
                                               'error': str(e)}).encode(), addr)

    def error_received(self, exc: Exception) -> None:
        super().error_received(exc)


def parse_args():
    parser = argparse.ArgumentParser(description='A UDP server to sink traffics and collect statics')
    parser.add_argument('-p', '--port', default=DEFAULT_UDP_CONTROL_PORT, help='The UDP port to listen on')
    parser.add_argument('-w', '--wait', default=DEFAULT_RUNNING_PERIOD, type=int,
                        help='The duration that the server will be running')
    args = parser.parse_args()
    return args


async def start_server(port, duration):
    logger.info(f'Start TCP control server on {DEFAULT_TCP_CONTROL_PORT}, control server on {port}, '
                f'data sink on {DEFAULT_UDP_DATA_SINK_PORT}, data pour on {DEFAULT_UDP_DATA_POUR_PORT}')
    loop = asyncio.get_running_loop()
    server_control_tcp = \
        await loop.create_server(lambda: TcpControlServerProtocol(), host='0.0.0.0', port=DEFAULT_TCP_CONTROL_PORT)
    transport_control, protocol_control = \
        await loop.create_datagram_endpoint(lambda: UdpControlServerProtocol(), local_addr=('0.0.0.0', port))
    transport_data_sink, protocol_data_sink = \
        await loop.create_datagram_endpoint(lambda: UdpDataSinkServerProtocol(),
                                            local_addr=('0.0.0.0', DEFAULT_UDP_DATA_SINK_PORT))
    transport_data_pour, protocol_data_pour = \
        await loop.create_datagram_endpoint(lambda: UdpDataPourServerProtocol(),
                                            local_addr=('0.0.0.0', DEFAULT_UDP_DATA_POUR_PORT))
    try:
        await asyncio.sleep(duration)
    finally:
        server_control_tcp.close()
        transport_control.close()
        transport_data_sink.close()
        transport_data_pour.close()


def main():
    args = parse_args()
    port = args.port
    try:
        asyncio.run(start_server(port, args.wait))
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
