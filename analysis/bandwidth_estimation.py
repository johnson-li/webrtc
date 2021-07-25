import os
import numpy as np
from experiment.base import RESULTS_PATH
from utils.base import RESULT_DIAGRAM_PATH
from matplotlib import pyplot as plt


def main():
    log_path = os.path.join(RESULTS_PATH, 'bandwidth_estimation')
    bitrates = [int(f.split('.')[0]) for f in os.listdir(log_path)]
    bitrates = np.array(list(sorted(bitrates)))
    bitrates = bitrates[bitrates < 100]
    data = {}
    for bitrate in bitrates:
        bw_list = []
        for line in open(os.path.join(log_path, f'{bitrate}.log')).readlines():
            line = line.strip()
            if 'pac r.: ' in line:
                array = line.split(', ')
                for arr in array:
                    if arr.startswith('pac r.: '):
                        bw = int(arr[8:-5]) / 1024
                        bw_list.append(bw)
        bw_list = np.array(bw_list)
        data[bitrate] = np.percentile(bw_list, 50)
    fig = plt.figure(figsize=(6, 2))
    plt.rcParams.update({'font.size': 12})
    plt.plot(bitrates, [data[b] for b in bitrates], linewidth=4)
    plt.xlabel('Application layer bitrate (Mbps)')
    plt.ylabel('Measured\nbandwidth (Mbps)')
    plt.xlim((0, 90))
    print(f'Bitrates: {bitrates}')
    plt.tight_layout()
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'bandwidth_estimation.png'), dpi=600)


if __name__ == '__main__':
    main()
