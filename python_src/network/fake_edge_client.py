import time
import socket
import os


os.makedirs('/tmp/webrtc/logs/det', exist_ok=True)
target = open('/tmp/ns.ip').read().strip()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((target, 8128))
    print('Connected to the server')
    while 1:
        data = s.recv(1024)
        if not data:
            continue
        ts = time.monotonic()
        print(f'[{ts}] receive det')
        with open(f'/tmp/webrtc/logs/det/{ts}.log', 'w+') as f:
            f.write(data.decode())
