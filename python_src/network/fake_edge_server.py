import os
import time
import socket
import json
import random


processed = set()
root = '/tmp/webrtc/logs/frames'
if os.path.exists(root):
    files = os.listdir(root)
    processed.update(files)
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 8128))
    s.listen()
    conn, addr = s.accept()
    with conn:
        print(f"Connected by {addr}")
        while 1:
            if not os.path.exists(root):
                continue
            files = os.listdir(root)
            if files:
                for f in files:
                    if f not in processed:
                        processed.add(f)
                        print(f'[{time.monotonic()}] Receive frame {f}')
                        num = random.randint(0, 5)
                        regions = {"frame": f, "regions": [{"x": 1.1234, "y": 8.12521, "w": 2.321, "h": 9.1231} for i in range(num)]}
                        conn.sendall(json.dumps(regions).encode())

