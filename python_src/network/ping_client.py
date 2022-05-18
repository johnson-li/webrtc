import socket
import time


UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPClientSocket.setblocking(0)
target="195.148.127.230"
# target="127.0.0.1"
i=0
start = time.monotonic()
while 1:
    if time.monotonic() - start >= i * .1:
        bytesToSend = str(i).encode()
        ts1 = time.monotonic()
        UDPClientSocket.sendto(bytesToSend, (target, 8129))
        print(f'[{ts1}] Send: {i}')
        i += 1
    try:
        msg, addr = UDPClientSocket.recvfrom(1024)
        if msg:
            ts2 = time.monotonic()
            print(f'[{ts2}] Recv: {msg.decode()}')
    except Exception as e:
        pass


