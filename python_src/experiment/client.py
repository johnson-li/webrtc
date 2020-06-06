import asyncio


class ClientProtocol:
  def __init__(self, on_con_lost):
    self._on_con_lost = on_con_lost

  def connection_made(self, transport):
    self._transport = transport
    self._transport.sendto("register".encode())

  def datagram_received(self, data, addr):
    print("Received:", data.decode())

  def connection_lost(self, exc):
    print("Connection closed")
    self._on_con_lost.set_result(True)

  def error_received(self, exc):
    print("Error received: %s" % exc)


async def start_udp_client():
  loop = asyncio.get_running_loop()
  on_con_lost = loop.create_future()
  transport, protocol = await loop.create_datagram_endpoint(
      lambda: ClientProtocol(on_con_lost), remote_addr=('195.148.127.233', 4400))
  try:
    await on_con_lost
  finally:
    transport.close()


def main():
  asyncio.run(start_udp_client())


if __name__ == '__main__':
  main()

