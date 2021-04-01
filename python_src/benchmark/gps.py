import os
import time
import utils2.gps.gps as gps
from utils2.gps.watch_options import *
import json
import argparse


def parse_args():
    parser = argparse.ArgumentParser(description='Dump gps info periodically')
    parser.add_argument('-l', '--log', default='/tmp/webrtc/logs', help='The dir of logging')
    args = parser.parse_args()
    if not os.path.exists(args.log):
        os.makedirs(args.log)
    return args


def read(log_path):
    session = gps(mode=WATCH_ENABLE)
    try:
        while True:
            report = session.next()
            if report['class'] == 'DEVICE':
                session.close()
                session = gps(mode=WATCH_ENABLE)
                continue
            elif report['class'] == 'TPV':
                ts = int(time.monotonic() * 1000)
                gps_time = report.get('time', None)
                lat = report.get('lat', None)
                lon = report.get('lon', None)
                track = report.get('track', None)
                speed = report.get('speed', None)
                if gps_time and lat and lon:
                    data = {'time': gps_time, 'lat': lat, 'lon': lon, 'track': track, 'speed': speed}
                    path = os.path.join(log_path, f'gps_{ts}.json')
                    json.dump(data, open(path, 'w+'))
    except StopIteration:
        print('GPSD has terminated')


def main():
    args = parse_args()
    log = args.log
    read(log)


if __name__ == '__main__':
    main()
