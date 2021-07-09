import os
import json
import time
import argparse
import asyncio
from asyncio import transports
from typing import Tuple
from pathlib import Path
from benchmark.config import *
from utils2.logging import logging
from benchmark import UdpClientProtocol, TcpProtocol
from uuid import uuid4
import aioconsole

logger = logging.getLogger(__name__)
UDP_DATA_TRANSPORTS = []
DURATION = 0
TERMINATED = False
PACKET_SIZE = 1024
TARGET_IP = ''
BIT_RATE = 0
PROBING_DELAY = 10
BUFFER = bytearray('buffer'.encode())
CLIENT_ID = str(uuid4())
LOG_PATH = ''
SERVICE = ''
EXIT_FUTURE: asyncio.Future
TRANSPORT = None
FPS = 10
FINISHED = False


class UdpClientProbingProtocol(UdpClientProtocol):
    def __init__(self, control_transport) -> None:
        super().__init__(control_transport)
        self._sequence = 0
        self._buffer = bytearray(1000)
        self._buffer[:ID_LENGTH] = CLIENT_ID.encode()
        self._last_receiving_timestamp = time.monotonic()
        self._last_print = 0

    async def probe(self):
        now = time.monotonic()
        time_diff = now - self._start_ts
        wait = self._sequence * PROBING_DELAY / 1000.0 - time_diff
        if wait > 0:
            await asyncio.sleep(wait)
        now = time.monotonic()
        self._buffer[ID_LENGTH: ID_LENGTH + PACKET_SEQUENCE_BYTES] = \
            self._sequence.to_bytes(PACKET_SEQUENCE_BYTES, BYTE_ORDER)
        self._statics['probing_sent'].append((now, self._sequence))
        self._transport.sendto(self._buffer)
        self._sequence += 1
        if now - self._start_ts < DURATION and not TERMINATED:
            if now - self._last_print > 10:
                print(f'Time spent: {int(now - self._start_ts)} s')
                self._last_print = now
            asyncio.create_task(self.probe())
        else:
            path = os.path.join(LOG_PATH, f'probing_client_{CLIENT_ID}.log')
            with open(path, 'w+') as f:
                json.dump(self._statics, f)
                logger.info(f'Dump statics data to {path}')
            for i in range(10):
                await asyncio.sleep(.2)
                self._transport.sendto('T'.encode())
            self._control_transport.write(json.dumps({'id': CLIENT_ID, 'request': {'type': 'statics'}}).encode())

    def connection_made(self, transport: transports.BaseTransport) -> None:
        super().connection_made(transport)
        asyncio.create_task(self.probe())

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        sequence = int.from_bytes(data[ID_LENGTH: ID_LENGTH + PACKET_SEQUENCE_BYTES], BYTE_ORDER)
        self._statics['probing_received'].append((time.monotonic(), sequence, len(data)))


class UdpClientDataSinkProtocol(UdpClientProtocol):
    def __init__(self, control_transport) -> None:
        super().__init__(control_transport)
        self._sequence = 0

    async def sink(self):
        now = time.monotonic()
        if FPS:
            period = 1000 // FPS
            time_diff = int((now - self._start_ts) * 1000 / period) * period / 1000
        else:
            time_diff = now - self._start_ts
        wait = len(BUFFER) * 8 * self._sequence / BIT_RATE - time_diff
        if wait > 0:
            await asyncio.sleep(wait)
        BUFFER[ID_LENGTH: ID_LENGTH + PACKET_SEQUENCE_BYTES] = \
            self._sequence.to_bytes(PACKET_SEQUENCE_BYTES, BYTE_ORDER)
        self._statics['udp_sink'].append((time.monotonic(), self._sequence, len(BUFFER)))
        self._sequence += 1
        self._transport.sendto(BUFFER)
        if time.monotonic() - self._start_ts < DURATION:
            asyncio.create_task(self.sink())
        else:
            self._statics['fps'] = FPS
            self._statics['bitrate'] = BIT_RATE
            self._statics['pkg_size'] = PACKET_SIZE
            with open(os.path.join(LOG_PATH, f'udp_client_{CLIENT_ID}.log'), 'w+') as f:
                json.dump(self._statics, f)
            self._control_transport.write(json.dumps({'id': CLIENT_ID, 'request': {'type': 'statics'}}).encode())

    def connection_made(self, transport: transports.BaseTransport) -> None:
        super().connection_made(transport)
        asyncio.create_task(self.sink())


class UdpClientDataPourProtocol(UdpClientProtocol):
    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        if len(data) == 1 and data[0] == 'T'.encode()[0]:
            with open(os.path.join(LOG_PATH, 'udp_client.log'), 'w+') as f:
                json.dump(self._statics, f)
            global FINISHED
            if not FINISHED:
                FINISHED = True
                self._control_transport.write(json.dumps({'id': CLIENT_ID, 'request': {'type': 'statics'}}).encode())
            return
        sequence = int.from_bytes(data[: PACKET_SEQUENCE_BYTES], BYTE_ORDER)
        self._statics['udp_pour'].append((time.monotonic(), sequence, len(data)))

    def connection_made(self, transport: transports.BaseTransport) -> None:
        super().connection_made(transport)
        self._transport.sendto(json.dumps({'id': CLIENT_ID, 'command': 'start', 'packet_size': PACKET_SIZE, 'fps': FPS,
                                           'bitrate': BIT_RATE, 'duration': DURATION}).encode())


class TcpClientControlProtocol(TcpProtocol):
    def __init__(self) -> None:
        super().__init__()
        self._buffer = ""

    def connection_made(self, transport: transports.BaseTransport) -> None:
        super().connection_made(transport)
        if SERVICE == 'udp_sink':
            self._transport.write(json.dumps({'id': CLIENT_ID, 'request': {'type': 'udp_sink',
                                                                           'fps': FPS,
                                                                           'bitrate': BIT_RATE}}).encode())
        elif SERVICE == 'udp_pour':
            self._transport.write(json.dumps({'id': CLIENT_ID, 'request': {'type': 'udp_pour',
                                                                           'fps': FPS,
                                                                           'bitrate': BIT_RATE}}).encode())
        elif SERVICE == 'probing':
            self._transport \
                .write(json.dumps({'id': CLIENT_ID, 'request': {'type': 'probing', 'delay': PROBING_DELAY}}).encode())

    def data_received(self, data: bytes) -> None:
        data = data.decode().strip()
        self._buffer += data
        try:
            data = json.loads(self._buffer)
            self._buffer = ''
        except json.decoder.JSONDecodeError as e:
            # logger.info(f'Response partially read ({len(self._buffer)}), wait for more bytes')
            return
        if data['status'] == 1 and data['id'] == CLIENT_ID:
            logger.info(f'Found target service, type: {data["type"]}, '
                        f'protocol: {data.get("protocol", None)}, port: {data.get("port", None)}')
            loop = asyncio.get_running_loop()
            if data['type'] == 'sink' and data.get('protocol', None) == 'UDP':
                asyncio.create_task(loop.create_datagram_endpoint(lambda: UdpClientDataSinkProtocol(self._transport),
                                                                  remote_addr=(TARGET_IP, data['port'])))
            elif data['type'] == 'pour' and data.get('protocol', None) == 'UDP':
                asyncio.create_task(loop.create_datagram_endpoint(lambda: UdpClientDataPourProtocol(self._transport),
                                                                  remote_addr=(TARGET_IP, data['port'])))
            elif data['type'] == 'probing':
                asyncio.create_task(loop.create_datagram_endpoint(lambda: UdpClientProbingProtocol(self._transport),
                                                                  remote_addr=(TARGET_IP, data['port'])))
            elif data['type'] == 'statics':
                statics = data['statics']
                path = os.path.join(LOG_PATH, f'server_{CLIENT_ID}.log')
                with open(path, 'w+') as f:
                    json.dump(statics, f)
                logger.info(f'Dump statics data to {path}')
                EXIT_FUTURE.set_result(True)
            else:
                logger.error(f'Unknown response type: {data["type"]}')
        else:
            logger.error(f"Server error: {data['message']}")


async def start_client(target_ip, target_port):
    loop = asyncio.get_running_loop()
    global EXIT_FUTURE, TRANSPORT
    EXIT_FUTURE = loop.create_future()
    TRANSPORT, protocol = \
        await loop.create_connection(lambda: TcpClientControlProtocol(), host=target_ip, port=target_port)


def parse_args():
    parser = argparse.ArgumentParser(description='A UDP client to flood the server')
    parser.add_argument('-s', '--server', default='127.0.0.1', help='The IP address of the UDP server')
    parser.add_argument('-p', '--port', default=DEFAULT_TCP_CONTROL_PORT, type=int, help='The port of the UDP server')
    parser.add_argument('-d', '--data-rate', default=DEFAULT_DATA_RATE, type=int,
                        help='The client\'s data rate of sending packets')
    parser.add_argument('-a', '--packet-size', default=DEFAULT_PACKET_SIZE, type=int,
                        help='The payload size of the UDP packets')
    parser.add_argument('-t', '--duration', default=15, type=int, help='The duration of running the data protocol')
    parser.add_argument('-r', '--probing-delay', default=10, type=float,
                        help='The interval of sending continuous probing packets')
    parser.add_argument('-l', '--logger', default='/tmp/webrtc/logs', help='The path of statics log')
    parser.add_argument('-b', '--service', choices=['udp_sink', 'udp_pour', 'probing'], default='udp_sink',
                        help='Specify the type of service')
    parser.add_argument('-f', '--fps', default=0, type=int, help='FPS')
    args = parser.parse_args()
    global TARGET_IP, DURATION, BUFFER, BIT_RATE, LOG_PATH, SERVICE, FPS, PACKET_SIZE, PROBING_DELAY
    PACKET_SIZE = args.packet_size
    FPS = args.fps
    TARGET_IP = args.server
    DURATION = args.duration
    BUFFER = bytearray(PACKET_SIZE)
    BUFFER[:ID_LENGTH] = CLIENT_ID.encode()
    BIT_RATE = args.data_rate
    LOG_PATH = args.logger
    Path(LOG_PATH).mkdir(parents=True, exist_ok=True)
    SERVICE = args.service
    PROBING_DELAY = args.probing_delay
    return args


async def wait():
    print('press "stop" to finish experiment:\n')
    stdin, stdout = await aioconsole.get_standard_streams()
    global TERMINATED
    while not TERMINATED:
        line = await stdin.readline()
        line = line.strip()
        if line == b'stop':
            print('Stopping...')
            TERMINATED = True
            # break
        else:
            print('Please only input "stop", try again:\n')

        # async for line in stdin:
        #     line = line.strip()
        #     if line == b'stop':
        #         print('Stopping...')
        #         global TERMINATED
        #         TERMINATED = True
        #         print(dir(stdin))
        #         stdin.close()
        #     else:
        #         print('Please only input "stop", try again:\n')
        # print('asdfasdf')


async def start(target_port):
    asyncio.create_task(start_client(TARGET_IP, target_port))
    # await wait()
    await asyncio.sleep(3)
    await EXIT_FUTURE
    TRANSPORT.close()


def main():
    args = parse_args()
    target_port = args.port
    try:
        asyncio.run(start(target_port))
        # asyncio.run(start_client(TARGET_IP, target_port))
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()