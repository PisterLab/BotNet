"""
Plot a stat over another stat.

Example:
    python plot.py --inputfolder simData/numMotes_50/ -x chargeConsumed --y aveLatency
"""
from __future__ import print_function

# =========================== imports =========================================

# standard
from builtins import range
import os
import argparse
import json
import glob
from collections import OrderedDict
import numpy as np

# third party
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ============================ defines ========================================

KPIS = [
    'latency_max_s',
    'latency_avg_s',
    'latencies',
    'lifetime_AA_years',
    'sync_time_s',
    'join_time_s',
    'upstream_num_lost'
]

# ============================ main ===========================================

def main(options):

    # init
    data = OrderedDict()

    # chose lastest results
    subfolders = list(
        [os.path.join(options.inputfolder, x) for x in os.listdir(options.inputfolder)]
    )
    subfolder = max(subfolders, key=os.path.getmtime)

    for key in options.kpis:
        # load data
        for file_path in sorted(glob.glob(os.path.join(subfolder, '*.kpi'))):
            curr_combination = os.path.basename(file_path)[:-8] # remove .dat.kpi
            with open(file_path, 'r') as f:

                # read kpi file
                kpis = json.load(f)

                # init data list
                data[curr_combination] = []

                # fill data list
                for run in kpis.values():
                    for mote in run.values():
                        if key in mote:
                            data[curr_combination].append(mote[key])

        # plot
        try:
            if key in ['lifetime_AA_years', 'latencies']:
                plot_cdf(data, key, subfolder)
            else:
                plot_box(data, key, subfolder)

        except TypeError as e:
            print("Cannot create a plot for {0}: {1}.".format(key, e))
    print("Plots are saved in the {0} folder.".format(subfolder))

# =========================== helpers =========================================

def plot_cdf(data, key, subfolder):
    for k, values in data.items():
        # convert list of list to list
        if type(values[0]) == list:
            values = sum(values, [])

        values = [None if value == 'N/A' else value for value in values]
        # compute CDF
        sorted_data = np.sort(values)
        yvals = np.arange(len(sorted_data)) / float(len(sorted_data) - 1)
        plt.plot(sorted_data, yvals, label=k)

    plt.xlabel(key)
    plt.ylabel("CDF")
    plt.legend()
    savefig(subfolder, key + ".cdf")
    plt.clf()

def plot_box(data, key, subfolder):
    plt.boxplot(list(data.values()))
    plt.xticks(list(range(1, len(data) + 1)), list(data.keys()))
    plt.ylabel(key)
    savefig(subfolder, key)
    plt.clf()

def savefig(output_folder, output_name, output_format="png"):
    # check if output folder exists and create it if not
    if not os.path.isdir(output_folder):
        os.makedirs(output_folder)

    # save the figure
    plt.savefig(
        os.path.join(output_folder, output_name + "." + output_format),
        bbox_inches     = 'tight',
        pad_inches      = 0,
        format          = output_format,
    )

def parse_args():
    # parse options
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--inputfolder',
        help       = 'The simulation result folder.',
        default    = 'simData',
    )
    parser.add_argument(
        '-k','--kpis',
        help       = 'The kpis to plot',
        type       = list,
        default    = KPIS
    )
    parser.add_argument(
        '--xlabel',
        help       = 'The x-axis label',
        type       = str,
        default    = None,
    )
    parser.add_argument(
        '--ylabel',
        help       = 'The y-axis label',
        type       = str,
        default    = None,
    )
    parser.add_argument(
        '--show',
        help       = 'Show the plots.',
        action     = 'store_true',
        default    = None,
    )
    return parser.parse_args()

if __name__ == '__main__':

    options = parse_args()

    main(options)
