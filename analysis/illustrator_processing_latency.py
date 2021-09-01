import os
import numpy as np
from utils.base import RESULT_DIAGRAM_PATH
from matplotlib import pyplot as plt

PATH = '/tmp/webrtc/logs/darknet.log'


def main():
    vals = []
    for line in open(PATH).readlines():
        line = line.strip()
        if line.startswith(': Predicted in '):
            val = line.split(' ')[3]
            val = float(val)
            vals.append(val)
    plt.figure()
    x = np.arange(len(vals))
    y = vals
    plt.plot(x, y)
    plt.xlabel('Frame sequence')
    plt.ylabel('Processing latency (ms)')
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'edge_processing_latency.png'), dpi=600)
    print(f'Avg. processing latency: {np.average(vals)} ms')


if __name__ == '__main__':
    main()
