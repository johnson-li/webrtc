from serial import Serial
import os
import argparse
import time
from multiprocessing import Pool, Process, shared_memory
from benchmark.config import SINR_ARRAY_BUFFER_SIZE, BYTE_ORDER


def open_serial(path='/dev/ttyUSB3'):
    ser = Serial(path, timeout=0)
    return ser


def write(ser, log_dir, delay=100):
    cmd = 'AT+CCLK?;+CREG?;+CSQ;+QNWINFO;+QSPN;+QENG="servingcell";+QENG="neighbourcell";\r\n'
    cmd = 'AT+CCLK?;+QENG="servingcell";\r\n'
    cmd = 'AT+QENG="servingcell";\r\n'
    # log = os.path.join(log_dir, f'quectel_server.log')
    while 1:
        # ts = int(time.monotonic() * 1000)
        ser.write(cmd.encode())
        # with open(log, 'a+') as f:
        #     f.write(str(ts))
        #     f.write('\n')
        time.sleep(delay / 1000.0)


def read(ser, log_dir):
    shm_a = shared_memory.SharedMemory(name='reliable', create=True, size=(SINR_ARRAY_BUFFER_SIZE + 1) * 8)
    index = 0
    while 1:
        res = ser.readall()
        res = res.decode()
        sinr = None
        if res:
            print(res)
            ts = int(time.monotonic() * 1000)
            for line in res.split('\n'):
                if 'NR5G-NSA' in line:
                    sinr = int(line.split(',')[5])
            if sinr is not None:
                shm_a.buf[4 + 8 * (index % SINR_ARRAY_BUFFER_SIZE): 4 + 8 * (index % SINR_ARRAY_BUFFER_SIZE) + 4] = \
                    int(sinr).to_bytes(length=4, byteorder=BYTE_ORDER)
                shm_a.buf[4 + 8 * (index % SINR_ARRAY_BUFFER_SIZE) + 4: 4 + 8 * (index % SINR_ARRAY_BUFFER_SIZE) + 8] = \
                    int(ts).to_bytes(length=4, byteorder=BYTE_ORDER)
                shm_a.buf[: 4] = index.to_bytes(length=4, byteorder=BYTE_ORDER)
                index += 1

            log = os.path.join(log_dir, f'quectel_{ts}.log')
            with open(log, 'a+') as f:
                f.write(res)


def parse_args():
    parser = argparse.ArgumentParser(description='Dump cellular info periodically')
    parser.add_argument('-l', '--log', default='/tmp/webrtc/logs/quectel', help='The dir of logging')
    parser.add_argument('-d', '--delay', default=10, type=int, help='The interval of query in milliseconds')
    args = parser.parse_args()
    if not os.path.exists(args.log):
        os.makedirs(args.log)
    return args


def main():
    args = parse_args()
    delay = args.delay
    log = args.log
    ser = open_serial()
    process_write = Process(target=write, args=(ser, log, delay))
    process_read = Process(target=read, args=(ser, log))
    process_read.start()
    process_write.start()
    process_read.join()
    process_write.join()


if __name__ == '__main__':
    main()
