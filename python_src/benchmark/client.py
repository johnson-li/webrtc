import os
import json
import time
import argparse
import asyncio
from asyncio import transports
from typing import Tuple

from benchmark.config import *
from utils2.logging import logging
from benchmark import UdpClientProtocol, TcpProtocol
from uuid import uuid4

logger = logging.getLogger(__name__)
UDP_DATA_TRANSPORTS = []
DURATION = 0
TARGET_IP = ''
BIT_RATE = 0
BUFFER = bytearray('buffer'.encode())
CLIENT_ID = str(uuid4())
LOG_FILE = ''
SERVICE = ''
EXIT_FUTURE: asyncio.Future


class UdpClientDataSinkProtocol(UdpClientProtocol):
    def __init__(self) -> None:
        super().__init__()
        self._sequence = 0

    async def sink(self):
        wait = len(BUFFER) * 8 * self._sequence / BIT_RATE - (time.time() - self._start_ts)
        if wait > 0:
            await asyncio.sleep(wait)
        BUFFER[ID_LENGTH: ID_LENGTH + PACKET_SEQUENCE_BYTES] = \
            self._sequence.to_bytes(PACKET_SEQUENCE_BYTES, BYTE_ORDER)
        self._statics.append((time.time(), self._sequence, len(BUFFER)))
        self._sequence += 1
        self._transport.sendto(BUFFER)
        if time.time() - self._start_ts < DURATION:
            asyncio.create_task(self.sink())
        else:
            json.dump(self._statics, open(LOG_FILE, 'w+'))
            EXIT_FUTURE.set_result(True)

    def connection_made(self, transport: transports.BaseTransport) -> None:
        super().connection_made(transport)
        asyncio.create_task(self.sink())


class UdpClientDataPourProtocol(UdpClientProtocol):
    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        if len(data) == 1 and data[0] == 'T'.encode()[0]:
            EXIT_FUTURE.set_result(True)
            json.dump(self._statics, open(LOG_FILE, 'w+'))
            return
        sequence = int.from_bytes(data[: PACKET_SEQUENCE_BYTES], BYTE_ORDER)
        self._statics.append((time.time(), sequence, len(data)))

    def connection_made(self, transport: transports.BaseTransport) -> None:
        super().connection_made(transport)
        self._transport.sendto(json.dumps({'id': CLIENT_ID, 'command': 'start', 'packet_size': 1024,
                                           'bitrate': BIT_RATE, 'duration': DURATION}).encode())


class TcpClientControlProtocol(TcpProtocol):
    def connection_made(self, transport: transports.BaseTransport) -> None:
        super().connection_made(transport)
        if SERVICE == 'udp_sink':
            self._transport.write(json.dumps({'id': CLIENT_ID, 'request': {'type': 'udp_sink',
                                                                           'bitrate': BIT_RATE}}).encode())
        elif SERVICE == 'udp_pour':
            self._transport.write(json.dumps({'id': CLIENT_ID, 'request': {'type': 'udp_pour',
                                                                           'bitrate': BIT_RATE}}).encode())

    def data_received(self, data: bytes) -> None:
        data = data.decode().strip()
        data = json.loads(data)
        if data['status'] == 1 and data['id'] == CLIENT_ID:
            logger.info(f'Found target service, type: {data["type"]}, '
                        f'protocol: {data["protocol"]}, port: {data["port"]}')
            loop = asyncio.get_running_loop()
            if data['type'] == 'sink' and data['protocol'] == 'UDP':
                asyncio.create_task(loop.create_datagram_endpoint(lambda: UdpClientDataSinkProtocol(),
                                                                  remote_addr=(TARGET_IP, data['port'])))
            elif data['type'] == 'pour' and data['protocol'] == 'UDP':
                asyncio.create_task(loop.create_datagram_endpoint(lambda: UdpClientDataPourProtocol(),
                                                                  remote_addr=(TARGET_IP, data['port'])))
        else:
            logger.error(f"Server error: {data['message']}")


async def start_client(target_ip, target_port):
    loop = asyncio.get_running_loop()
    global EXIT_FUTURE
    EXIT_FUTURE = loop.create_future()
    transport, protocol = \
        await loop.create_connection(lambda: TcpClientControlProtocol(), host=target_ip, port=target_port)
    try:
        await EXIT_FUTURE
    finally:
        transport.close()


def parse_args():
    parser = argparse.ArgumentParser(description='A UDP client to flood the server')
    parser.add_argument('-s', '--server', default='127.0.0.1', help='The IP address of the UDP server')
    parser.add_argument('-p', '--port', default=DEFAULT_TCP_CONTROL_PORT, type=int, help='The port of the UDP server')
    parser.add_argument('-d', '--data-rate', default=DEFAULT_DATA_RATE, type=int,
                        help='The client\'s data rate of sending packets')
    parser.add_argument('-a', '--packet-size', default=DEFAULT_PACKET_SIZE, type=int,
                        help='The payload size of the UDP packets')
    parser.add_argument('-t', '--duration', default=10, help='The duration of running the data protocol')
    parser.add_argument('-l', '--logger', default='/tmp/client_statics.log', help='The path of statics log')
    parser.add_argument('-b', '--service', choices=['udp_sink', 'udp_pour'], default='udp_sink',
                        help='Specify the type of service')
    args = parser.parse_args()
    global TARGET_IP, DURATION, BUFFER, BIT_RATE, LOG_FILE, SERVICE
    TARGET_IP = args.server
    DURATION = args.duration
    BUFFER = bytearray(os.urandom(args.packet_size))
    BUFFER[:ID_LENGTH] = CLIENT_ID.encode()
    BIT_RATE = args.data_rate
    LOG_FILE = args.logger
    SERVICE = args.service
    return args


def main():
    args = parse_args()
    target_port = args.port
    try:
        asyncio.run(start_client(TARGET_IP, target_port))
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
