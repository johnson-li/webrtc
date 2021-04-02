import matplotlib.pyplot as plt
import os
from utils.base import RESULT_DIAGRAM_PATH


def rtt_over_bandwidth_usage():
    # SNR -> Uplink,Downlink -> Bandwidth -> RTT (min, avg, max)
    data = {
        20: {
            'ul': {
                '0 Mbps': [9.123, 11.412, 16.274],
                '1 Mbps': [9.053, 15.010, 22.477],
                '5 Mbps': [9.991, 21.900, 37.421],
                '10 Mbps': [14.597, 23.438, 33.395],
                '20 Mbps': [12.266, 22.143, 30.863],
                '30 Mbps': [15.088, 25.297, 38.101],
                '40 Mbps': [15.032, 22.646, 36.062],
                '50 Mbps': [13.561, 20.619, 36.214],
                '60 Mbps': [14.242, 21.798, 29.508],
                '70 Mbps': [16.597, 24.801, 35.675],
                '80 Mbps': [15.617, 23.887, 33.670],
                '90 Mbps': [119.841, 159.789, 194.647],
                '100 Mbps': [112.302, 154.771, 194.421],
            },
            'dl': {
                '0 Mbps': [9.541, 10.609, 15.567],
                '1 Mbps': [8.779, 13.665, 21.738],
                '5 Mbps': [10.525, 14.430, 22.622],
                '10 Mbps': [10.483, 15.554, 21.571],
                '20 Mbps': [9.484, 14.855, 22.461],
                '30 Mbps': [9.391, 14.390, 20.693],
                '40 Mbps': [10.457, 14.468, 23.574],
                '50 Mbps': [10.389, 13.903, 18.493],
                '60 Mbps': [9.495, 14.107, 18.503],
                '70 Mbps': [9.688, 14.007, 22.332],
                '80 Mbps': [9.656, 14.915, 24.097],
                '90 Mbps': [9.496, 14.418, 28.465],
                '100 Mbps': [11.434, 15.601, 21.694],
            }
        },
        30: {
            'ul': {
                '0 Mbps': [9.134, 11.071, 15.576],
                '1 Mbps': [9.487, 12.603, 16.028],
                '5 Mbps': [9.584, 18.774, 32.105],
                '10 Mbps': [14.284, 23.403, 39.544],
                '20 Mbps': [11.699, 21.769, 34.150],
                '30 Mbps': [13.639, 23.600, 35.075],
                '40 Mbps': [14.089, 22.649, 34.091],
                '50 Mbps': [13.713, 21.929, 38.611],
                '60 Mbps': [14.486, 22.214, 36.604],
                '70 Mbps': [14.119, 25.228, 55.681],
                '80 Mbps': [16.608, 24.023, 39.678],
                '90 Mbps': [15.184, 24.006, 36.712],
                '100 Mbps': [16.622, 23.976, 40.128],
                '110 Mbps': [14.617, 20.755, 37.123],
                '120 Mbps': [17.681, 41.769, 67.722],
                '130 Mbps': [96.329, 124.593, 149.848],
                '140 Mbps': [80.772, 119.802, 145.562],
            },
            'dl': {
                '0 Mbps': [9.422, 11.265, 16.039],
                '1 Mbps': [9.533, 13.129, 19.744],
                '5 Mbps': [10.244, 13.291, 16.528],
                '10 Mbps': [10.393, 13.639, 17.602],
                '20 Mbps': [9.516, 13.790, 23.548],
                '30 Mbps': [9.357, 13.081, 20.547],
                '40 Mbps': [10.396, 13.470, 17.861],
                '50 Mbps': [9.852, 14.444, 22.411],
                '60 Mbps': [9.578, 14.609, 25.950],
                '70 Mbps': [10.706, 14.503, 22.267],
            }
        },
        15: {
            'ul': {
                '0 Mbps': [21.652, 33.524, 41.208],
                '1 Mbps': [14.697, 26.474, 39.122],
                '5 Mbps': [14.035, 26.851, 40.611],
                '10 Mbps': [18.999, 27.299, 40.105],
                '20 Mbps': [233.575, 319.644, 394.897],
                '30 Mbps': [253.721, 363.539, 501.408],
            },
            'dl': {
                '0 Mbps': [21.538, 33.936, 55.058],
                '1 Mbps': [21.661, 33.648, 52.685],
                '5 Mbps': [21.495, 34.781, 49.595],
                '10 Mbps': [21.599, 33.329, 47.342],
                '20 Mbps': [20.617, 32.340, 51.555],
                '30 Mbps': [20.472, 33.608, 46.652],
                '40 Mbps': [21.437, 34.928, 58.362],
            }
        },
    }
    plt.figure()
    for snr, d in data.items():
        x_ul, x_dl, ul, dl = [], [], [], []
        for x, val in d['ul'].items():
            x_ul.append(x.split(' ')[0])
            ul.append(val[1])
        for x, val in d['dl'].items():
            x_dl.append(x.split(' ')[0])
            dl.append(val[1])
        plt.plot(x_ul, ul)
        plt.plot(x_dl, dl)
        plt.legend(['uplink', 'downlink'])
        plt.xlabel('Bandwidth usage (Mbps)')
        plt.ylim([0, 80])
        plt.ylabel('RTT (ms)')
        plt.title(f'SNR: {snr}')
        plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'static_rtt_{snr}.png'))
        plt.show()





def main():
    rtt_over_bandwidth_usage()


if __name__ == '__main__':
    main()
