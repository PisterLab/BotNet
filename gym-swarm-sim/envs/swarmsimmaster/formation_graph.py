import matplotlib.pyplot as plt
import os
import numpy as np

plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["font.size"] = 12
ALL_MODELS = ["full", "disk", "friis_lower", "pister_hack"]
DISK_RANGES = [3, 10, 20]
MODEL_LABEL = ["Full Connectivity", "Disk R=3", "Disk R=10", "Disk R=20", "Probabilistic Disk", "Experimental Randomness"]
colors = [
    '#1f77b4',  # muted blue
    '#ff7f0e',  # safety orange
    '#2ca02c',  # cooked asparagus green
    '#d62728',  # brick red
    '#9467bd',  # muted purple
    '#8c564b',  # chestnut brown
    '#e377c2',  # raspberry yogurt pink
    '#7f7f7f',  # middle gray
    '#bcbd22',  # curry yellow-green
    '#17becf'  # blue-teal
]

markers = ["o", "v", "P", "D", "*", "p"]
AGENT_NUMS = [25, 50, 100, 150, 200, 250, 300]
ALPHA = 0.8


TIMESTEP = False
for TIMESTEP in [True, False]:
    i = 0
    ax = plt.subplot(111)

    for model in ALL_MODELS:

        if model != "disk":
            err = []
            errorbar = []
            for num_agents in AGENT_NUMS:
                data_dir = "logs/line_" + model + "_" + str(num_agents)
                data = []
                for f in os.listdir(data_dir):
                    x = np.load(data_dir + "/" + f)
                    data.append(x)
                data = np.array(data)

                if not TIMESTEP:
                    e = data[:, 1]
                else:
                    e = data[:, 0]
                mean_e = np.mean(e)
                err.append(mean_e)
                errorbar.append(np.std(e) / np.sqrt(len(e)))

            ax.plot(AGENT_NUMS, err, label=MODEL_LABEL[i], color=colors[i], alpha=ALPHA, marker=markers[i], markersize=10)
            ax.fill_between(AGENT_NUMS, np.array(err) - np.array(errorbar), np.array(err) + np.array(errorbar), alpha = 0.5)

            i += 1

        else:
            for q in DISK_RANGES:
                err = []
                errorbar = []

                for num_agents in AGENT_NUMS:
                    data_dir = "logs/line_" + model + "_" + str(q) + "_" + str(num_agents)

                    data = []
                    for f in os.listdir(data_dir):
                        x = np.load(data_dir + "/" + f)
                        data.append(x)
                    data = np.array(data)

                    if not TIMESTEP:
                        e = data[:, 1]
                    else:
                        e = data[:, 0]
                    mean_e = np.mean(e)
                    err.append(mean_e)
                    errorbar.append(np.std(e) / np.sqrt(len(e)))

                ax.plot(AGENT_NUMS, err, label=MODEL_LABEL[i], color=colors[i], alpha=ALPHA, marker=markers[i],
                        markersize=10)
                ax.fill_between(AGENT_NUMS, np.array(err) - np.array(errorbar), np.array(err) + np.array(errorbar),
                                alpha=0.5)
                i += 1

    # Hide the right and top spines
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    # Only show ticks on the left and bottom spines
    ax.yaxis.set_ticks_position('left')
    ax.xaxis.set_ticks_position('bottom')

    plt.xlim([25, 300])
    plt.xlabel("Number of Agents" )
    plt.yscale("log")
    if not TIMESTEP:
        plt.ylabel("Line Formation Residual Error")
    else:
        plt.ylabel("Timesteps to Formation Convergence")

        plt.legend(loc='lower right', ncol=2)

    if not TIMESTEP:
        plt.savefig("line_err.pdf")
    else:
        plt.savefig("line_time.pdf")

    plt.clf()