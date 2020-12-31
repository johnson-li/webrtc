import os
import argparse
import asyncio
import time
import json
from asyncio import transports
from aiohttp import web

from benchmark import UdpServerProtocol, TcpProtocol
from benchmark.config import *
from typing import Tuple
from utils2.logging import logging

logger = logging.getLogger(__name__)
STATICS = {}
POUR_CLIENTS = {}
routes = web.RouteTableDef()


class UdpDataPourServerProtocol(UdpServerProtocol):
    async def pour(self, client_id, buffer):
        info = POUR_CLIENTS[client_id]
        wait = len(buffer) * 8 * info['sequence'] / info['bitrate'] - \
               (time.perf_counter() - info['start_ts'])
        if wait > 0:
            await asyncio.sleep(wait)
        buffer[: PACKET_SEQUENCE_BYTES] = info['sequence'].to_bytes(PACKET_SEQUENCE_BYTES, BYTE_ORDER)
        buffer[PACKET_SEQUENCE_BYTES: PACKET_SEQUENCE_BYTES + TIMESTAMP_BYTES] = \
            (int(time.perf_counter() * 1000)).to_bytes(8, BYTE_ORDER)
        STATICS[client_id]['udp_pour'][info['sequence']] = \
            {'timestamp': int(time.perf_counter() * 1000), 'size': len(buffer)}
        info['sequence'] = info['sequence'] + 1
        self._transport.sendto(buffer, info['addr'])
        if time.perf_counter() - info['start_ts'] < info['duration']:
            asyncio.create_task(self.pour(client_id, buffer))
        else:
            for i in range(3):
                await asyncio.sleep(1)
                self._transport.sendto('T'.encode(), info['addr'])

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        data = json.loads(data.decode())
        client_id = data['id']
        cmd = data['command']
        POUR_CLIENTS[client_id] = {'start_ts': time.perf_counter(), 'addr': addr}
        if cmd == 'start':
            POUR_CLIENTS[client_id].update({'bitrate': data['bitrate'], 'duration': data['duration'], 'sequence': 0})
            STATICS.setdefault(client_id, {}).setdefault('udp_pour', {})
        asyncio.create_task(self.pour(client_id, bytearray(os.urandom(data['packet_size']))))


class UdpDataSinkServerProtocol(UdpServerProtocol):
    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        client_id = data[:ID_LENGTH].decode('utf-8')
        sequence = int.from_bytes(data[ID_LENGTH:ID_LENGTH + PACKET_SEQUENCE_BYTES], BYTE_ORDER)
        STATICS[client_id]['udp_sink'][sequence] = \
            {'timestamp': int(time.perf_counter() * 1000), 'size': len(data)}


class TcpDataPourServerProtocol(TcpProtocol):
    async def pour(self, client_id, buffer):
        try:
            sent = self._transport._sock.send(buffer)
        except BlockingIOError as e:
            sent = -1
        if sent > 0:
            STATICS[client_id]['tcp_pour'] \
                .append({'timestamp': int(time.perf_counter() * 1000), 'size': len(buffer)})
        asyncio.create_task(self.pour(client_id, buffer))

    def data_received(self, data: bytes) -> None:
        data = json.loads(data.decode('utf-8'))
        client_id = data['id']
        cmd = data['command']
        POUR_CLIENTS[client_id] = {'start_ts': time.perf_counter()}
        data_size = data['data_size']
        data_size = 100 * 1024
        if cmd == 'start':
            POUR_CLIENTS[client_id].update({'data_size': data_size})
            STATICS.setdefault(client_id, {}).setdefault('tcp_pour', {})
        asyncio.create_task(self.pour(client_id, bytearray(os.urandom(data_size))))


class TcpDataSinkServerProtocol(TcpProtocol):
    def __init__(self):
        super(TcpDataSinkServerProtocol, self).__init__()
        self._buf = bytes()
        self._id = None
        self._count = 0

    def connection_made(self, transport: transports.BaseTransport) -> None:
        super(TcpDataSinkServerProtocol, self).connection_made(transport)

    def data_received(self, data: bytes) -> None:
        if not self._id:
            self._buf += data
            if len(self._buf) >= 36:
                self._buf = self._buf[:36]
                self._id = self._buf.decode('utf-8')
                print(f'id: {self._id}')
        if self._id:
            STATICS[self._id]['tcp_sink'][self._count] = \
                {'timestamp': int(time.perf_counter() * 1000), 'size': len(data)}
            self._count += 1


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
                STATICS.setdefault(client_id, {}).setdefault('udp_sink', {})
                self._transport.write(json.dumps({'id': client_id, 'status': 1, 'type': 'sink', 'protocol': 'UDP',
                                                  'port': DEFAULT_UDP_DATA_SINK_PORT}).encode())
            elif request_type == 'udp_pour':
                self._transport.write(json.dumps({'id': client_id, 'status': 1, 'type': 'pour', 'protocol': 'UDP',
                                                  'port': DEFAULT_UDP_DATA_POUR_PORT}).encode())
            elif request_type == 'tcp_sink':
                STATICS.setdefault(client_id, {}).setdefault('tcp_sink', {})
                self._transport.write(json.dumps({'id': client_id, 'status': 1, 'type': 'sink', 'protocol': 'TCP',
                                                  'port': DEFAULT_TCP_DATA_SINK_PORT}).encode())
            elif request_type == 'tcp_pour':
                self._transport.write(json.dumps({'id': client_id, 'status': 1, 'type': 'pour', 'protocol': 'TCP',
                                                  'port': DEFAULT_TCP_DATA_POUR_PORT}).encode())
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
    parser.add_argument('-t', '--http-port', default=DEFAULT_HTTP_CONTROL_PORT, help='The HTTP port to listen on')
    parser.add_argument('-w', '--wait', default=DEFAULT_RUNNING_PERIOD, type=int,
                        help='The duration that the server will be running')
    args = parser.parse_args()
    return args


@routes.post('/request')
async def handle_request(request):
    data = await request.json()
    request_id = data['id']
    req = data['request']
    req_type = req['type']
    response = {'id': request_id, 'status': 1}
    if req_type == 'udp_echo':
        response = data
    elif req_type == 'udp_sink':
        STATICS[request_id] = {'udp_sink': {}}
        response.update({'type': 'udp_sink', 'protocol': 'UDP', 'port': DEFAULT_UDP_DATA_SINK_PORT})
    elif req_type == 'udp_pour':
        STATICS[request_id] = {'udp_pour': {}}
        response.update({'type': 'udp_pour', 'protocol': 'UDP', 'port': DEFAULT_UDP_DATA_POUR_PORT})
    elif req_type == 'statics':
        response.update({'type': 'statics', 'statics': STATICS[request_id]})
    elif req_type == 'tcp_sink':
        STATICS[request_id] = {'tcp_sink': {}}
        response.update({'type': 'tcp_sink', 'protocol': 'TCP', 'port': DEFAULT_TCP_DATA_SINK_PORT})
    elif req_type == 'tcp_pour':
        STATICS[request_id] = {'tcp_pour': []}
        response.update({'type': 'tcp_pour', 'protocol': 'TCP', 'port': DEFAULT_TCP_DATA_POUR_PORT})
    elif req_type == 'cleanup':
        STATICS.clear()
        response.update({'type': 'cleanup'})
    else:
        response.update({'status': -1, 'type': 'error', 'message': f'Invalid request type: {req_type}'})
    return web.json_response(response)


async def setup_http(port):
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def start_server(port, http_port, duration):
    logger.info(f'Start HTTP control server on {http_port}, TCP control server on {port}, '
                f'data sink on {DEFAULT_UDP_DATA_SINK_PORT}, data pour on {DEFAULT_UDP_DATA_POUR_PORT}')
    loop = asyncio.get_running_loop()
    server_control_tcp = \
        await loop.create_server(lambda: TcpControlServerProtocol(), host='0.0.0.0', port=DEFAULT_TCP_CONTROL_PORT)
    tcp_data_pour = await loop.create_server(lambda: TcpDataPourServerProtocol(), host='0.0.0.0',
                                             port=DEFAULT_TCP_DATA_POUR_PORT)
    tcp_data_sink = await loop.create_server(lambda: TcpDataSinkServerProtocol(), host='0.0.0.0',
                                             port=DEFAULT_TCP_DATA_SINK_PORT)
    transport_control, protocol_control = \
        await loop.create_datagram_endpoint(lambda: UdpControlServerProtocol(), local_addr=('0.0.0.0', port))
    transport_data_sink, protocol_data_sink = \
        await loop.create_datagram_endpoint(lambda: UdpDataSinkServerProtocol(),
                                            local_addr=('0.0.0.0', DEFAULT_UDP_DATA_SINK_PORT))
    transport_data_pour, protocol_data_pour = \
        await loop.create_datagram_endpoint(lambda: UdpDataPourServerProtocol(),
                                            local_addr=('0.0.0.0', DEFAULT_UDP_DATA_POUR_PORT))
    await setup_http(http_port)
    try:
        await asyncio.sleep(duration)
    finally:
        server_control_tcp.close()
        tcp_data_pour.close()
        tcp_data_sink.close()
        transport_control.close()
        transport_data_sink.close()
        transport_data_pour.close()


def main():
    args = parse_args()
    port = args.port
    http_port = args.http_port
    try:
        asyncio.run(start_server(port, http_port, args.wait))
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
