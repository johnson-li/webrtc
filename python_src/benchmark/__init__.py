import asyncio
from asyncio import transports


class UdpServerProtocol(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self._transport = None

    def connection_made(self, transport: transports.BaseTransport) -> None:
        self._transport = transport


class UdpClientProtocol(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self._transport = None

    def connection_made(self, transport: transports.BaseTransport) -> None:
        self._transport = transport


class TcpProtocol(asyncio.Protocol):
    def __init__(self) -> None:
        self._transport = None

    def connection_made(self, transport: transports.BaseTransport) -> None:
        self._transport = transport
