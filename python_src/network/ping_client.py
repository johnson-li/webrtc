import socket
import time


UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPClientSocket.settimeout(1)
bytesToSend = str.encode("T")
ts1 = time.monotonic()
try:
    UDPClientSocket.sendto(bytesToSend, ("195.148.127.230", 8129))
    msgFromServer = UDPClientSocket.recvfrom(1024)
    ts2 = time.monotonic()
    print(f'[{ts1}] RTT: {ts2 - ts1}')
except Exception:
    print(f'[{ts1}] RTT: -1')


