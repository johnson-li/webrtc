import os
import matplotlib.pyplot as plt

PATH = os.path.expanduser("~/Data/webrtc_exp5/25-10-2020_22-52-40")
FILE = f'{PATH}/analysis_latency.yolov5s.txt'

fig = plt.figure()


def draw(latencies, count):
    keys = sorted(latencies.keys())
    keys = keys[:count + 1]
    values = [latencies[k] for k in keys]
    ax = fig.add_subplot(111)
    ax.plot(keys, values, color='green')
    ax.set_aspect(2)
    plt.ylabel('Latency (ms)')
    plt.xlim(min(latencies.keys()), 500)
    plt.ylim(0, 50)
    plt.savefig(os.path.expanduser(f'~/Pictures/mobix/latencies/{keys[count]}.jpeg'), dpi=500)


def main():
    data = {}
    with open(FILE) as f:
        buffer = ""
        for line in f.readlines():
            if '===' in line:
                break
            if line.startswith('{'):
                if buffer:
                    d = eval(buffer)
                    data.update(d)
                    buffer = ''
            line = line.strip()
            buffer += line
    latencies = {}
    for k, v in data.items():
        if 'assembled_timestamp' in v and 'encoded_time' in v:
            latency = v['assembled_timestamp'] - v['encoded_time'] + -8382180.067
            sequence = int(v['frame_sequence'])
            latencies[sequence] = latency
    for i in range(len(latencies)):
        draw(latencies, i)


if __name__ == '__main__':
    main()
