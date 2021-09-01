import os
from matplotlib import pyplot as plt
import numpy as np
from experiment.base import RESULTS_PATH
from utils.base import RESULT_DIAGRAM_PATH
from sklearn.linear_model import LinearRegression
from analysis.probing import parse_sync, parse_signal_strength, parse_packets
import json


def main():
    probing_path = os.path.join(RESULTS_PATH, 'bandwidth_adaption_4')
    reg: LinearRegression = parse_sync(plot=False, path=probing_path)
    signal_data = parse_signal_strength(log_path=probing_path)
    uplink_packets, downlink_packets = parse_packets(reg, log_path=probing_path)
    pkg_size = uplink_packets[0][3]
    xrange = \
        (np.min(uplink_packets[uplink_packets[:, 1] > 0, 1]), np.max(uplink_packets[uplink_packets[:, 1] > 0, 1]))
    yrange = \
        (np.min(uplink_packets[uplink_packets[:, 2] > 0, 2]), np.max(uplink_packets[uplink_packets[:, 2] > 0, 2]))
    plt.rcParams['font.family'] = 'sans-serif'
    sent = uplink_packets[:, 1]
    arrival = uplink_packets[:, 2]
    sent = sent[arrival > 0]
    arrival = arrival[arrival > 0]

    fig, ax1 = plt.subplots(figsize=(6, 2))

    # Plot Estimated bandwidth and SINR
    LOG_PATH = os.path.join(RESULTS_PATH, 'bandwidth_adaption_4')
    signal_data = parse_signal_strength(log_path=LOG_PATH)
    f = sorted(filter(lambda x: x.startswith('reliable_client_'), os.listdir(LOG_PATH)))[-2]
    data = json.load(open(os.path.join(LOG_PATH, f)))
    pacing_log = np.array(data['pacing_rate_log'])
    x = pacing_log[:, 0]
    y = pacing_log[:, 1] / 1024 / 1024 * 8
    x -= np.min(x)
    ax1.plot(x, y)
    ax1.set_xlabel('Send time (s)                        ')
    ax1.set_ylabel('Bandwidth (Mbps)')
    ax1.set_ylim((0, 200))
    # ax1.set_xlim((np.min(x), np.max(x)))


    # Plot ground truth bandwidth
    window_size = .5
    ts_min = np.min(sent)
    arrival_data = ((arrival - ts_min) / window_size).astype(int)
    bandwidth_data = np.bincount(arrival_data)
    x = np.arange(bandwidth_data.shape[0]) * window_size
    y = bandwidth_data * pkg_size / window_size / 1024 / 1024 * 8
    y_range = [np.min(y) * 0.8, np.max(y) * 1.2]
    ax1.plot(x, y, 'y--', linewidth=1)
    ax1.set_xlim([np.min(x), np.max(x)])
    # ax1.set_ylim(y_range)
    ax1.set_ylabel('Bandwidth\n(Mbps)')
    ax1.set_xlabel('Sending timestamp (s)')
    ax1.legend(['Estimated bandwidth', 'Available bandwidth'])
    fig.tight_layout()
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'probing_est_bandwidth_ground.pdf'), dpi=600, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    main()
