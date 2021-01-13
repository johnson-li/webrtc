import time
import asyncio
from asyncio import transports


class UdpServerProtocol(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self._transport = None

    def connection_made(self, transport: transports.BaseTransport) -> None:
        self._transport = transport


class UdpClientProtocol(asyncio.DatagramProtocol):
    def __init__(self, control_transport) -> None:
        self._control_transport = control_transport
        self._transport = None
        self._start_ts = 0
        self._statics = {'udp_sink': [], 'udp_pour': []}

    def connection_made(self, transport: transports.BaseTransport) -> None:
        self._transport = transport
        self._start_ts = time.monotonic()


class TcpProtocol(asyncio.Protocol):
    def __init__(self) -> None:
        self._transport = None

    def connection_made(self, transport: transports.BaseTransport) -> None:
        self._transport = transport
