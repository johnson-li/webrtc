from experiment.base import DATA_PATH
from utils.base import RESULT_DIAGRAM_PATH
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import os
from scipy.interpolate import make_interp_spline, BSpline

# plt.rcParams.update({'font.size': 18})
TEXT_SIZE = 38


def draw_cdf(values, x_label, name, avg=False):
    font_size = 16
    values = np.array(values)
    values.sort()
    fig, ax = plt.subplots(figsize=(4, 2.5))
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
    plt.plot(x_new, y_new, color='red', linewidth=2)
    matplotlib.rcParams.update({'font.size': font_size})
    ax.tick_params(axis='both', which='major', labelsize=font_size)
    ax.tick_params(axis='both', which='minor', labelsize=font_size)
    plt.xlabel(x_label, size=font_size)
    plt.ylabel('CDF', size=font_size)
    plt.ylim([0, 1])
    fig.tight_layout(pad=.3)
    # if avg:
    #     plt.plot(np.mean(values).repeat(values.shape[0]), np.arange(0, 1, 1 / values.shape[0]), 'g--', linewidth=2)
    plt.savefig(os.path.join(RESULT_DIAGRAM_PATH, f'{name}'), dpi=600)
    plt.close(fig)


def init_figure_wide(figsize=(4, 2.5), font_size=16):
    matplotlib.rcParams.update({'font.size': font_size})
    fig, ax = plt.subplots(figsize=figsize)
    ax.tick_params(axis='both', which='major', labelsize=font_size)
    ax.tick_params(axis='both', which='minor', labelsize=font_size)
    # fig.tight_layout(pad=.3)
    return fig, ax, font_size
