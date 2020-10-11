import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# sock.bind(('0.0.0.0', 8084))
MESSAGE = b"H" * 1400
while 1:
    sock.sendto(MESSAGE, ("192.168.1.28", 8080))
# while True:
#     data, addr = sock.recvfrom(1024 * 1024)
#     print("received message: %d bytes" % len(data))
#     while 1:
#         sock.sendto(MESSAGE, addr)
