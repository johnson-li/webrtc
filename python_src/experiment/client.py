import asyncio
import argparse


class ClientProtocol:
  def __init__(self, on_con_lost, logger_path):
    self._on_con_lost = on_con_lost
    self._logger_file = open(logger_path, 'w') if logger_path else None

  def connection_made(self, transport):
    self._transport = transport
    self._transport.sendto("register".encode())

  def datagram_received(self, data, addr):
    data = data.decode()
    print("Received:", data)
    if self._logger_file:
      self._logger_file.write(data + "\n")

  def connection_lost(self, exc):
    print("Connection closed")
    self._on_con_lost.set_result(True)
    self._logger_file.close()

  def error_received(self, exc):
    print("Error received: %s" % exc)


async def start_udp_client(logger_path):
  loop = asyncio.get_running_loop()
  on_con_lost = loop.create_future()
  transport, protocol = await loop.create_datagram_endpoint(
      lambda: ClientProtocol(on_con_lost, logger_path), remote_addr=('195.148.127.233', 4400))
  try:
    await on_con_lost
  finally:
    transport.close()


def parse_args():
  parser = argparse.ArgumentParser(description="A UDP client that receives the server's detected objects")
  parser.add_argument('--logger', default="")
  return parser.parse_args()


def main():
  args = parse_args()
  logger_path = args.logger
  asyncio.run(start_udp_client(logger_path))


if __name__ == '__main__':
  main()

