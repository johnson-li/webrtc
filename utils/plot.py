from experiment.base import DATA_PATH
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import os
from scipy.interpolate import make_interp_spline, BSpline

# plt.rcParams.update({'font.size': 18})
TEXT_SIZE = 38
matplotlib.rc('font', size=TEXT_SIZE)
matplotlib.rc('axes', titlesize=TEXT_SIZE)


def draw_cdf(values, x_label, name, avg=False):
    values = np.array(values)
    values.sort()
    fig = plt.figure(figsize=(11, 11))
    y = np.arange(0, 1, 1 / values.shape[0])
    y_new = []
    x_new = []
    for i in range(values.shape[0]):
        v = values[i]
        if not x_new or v != x_new[-1]:
            x_new.append(v)
            y_new.append(y[i])
        elif v == x_new[-1] and y[i] > y_new[-1]:
            y_new[-1] = y[i]
    print(dict(zip(x_new, y_new)))
    x = np.linspace(np.min(x_new), np.max(x_new), 300)
    spl = make_interp_spline(x_new, y_new, 3)
    y = spl(x)
    plt.plot(x_new, y_new, color='red', linewidth=5)
    plt.xlabel(x_label)
    plt.ylabel('CDF')
    # if avg:
    #     plt.plot(np.mean(values).repeat(values.shape[0]), np.arange(0, 1, 1 / values.shape[0]), 'g--', linewidth=2)
    plt.savefig(os.path.join(DATA_PATH, f'{name}.png'), dpi=600, bbox_inches='tight')
    plt.show()
