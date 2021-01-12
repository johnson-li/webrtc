from experiment.base import DATA_PATH
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import os
from scipy.interpolate import make_interp_spline, BSpline

# plt.rcParams.update({'font.size': 18})
TEXT_SIZE = 38


def draw_cdf(values, x_label, name, avg=False):
    values = np.array(values)
    values.sort()
    plt.figure(figsize=(11, 11))
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


def init_figure_wide():
    text_size = 42
    matplotlib.rc('font', size=text_size, weight='normal')
    matplotlib.rc('axes', titlesize=text_size)
    plt.rcParams['axes.linewidth'] = 3
    fig, ax = plt.subplots(figsize=(20, 12), dpi=100)
    return fig, ax
