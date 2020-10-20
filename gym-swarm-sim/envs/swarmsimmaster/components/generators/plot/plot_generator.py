import matplotlib.pyplot as plt
import csv
import numpy as np
import pandas as pn
import os as os

# def plot_generator(file,directory, start, x_index, name, plot_type="line"):
#     with open(directory+"/"+file, 'r') as data:
#         plotter(data, directory, start, x_index, name, plot_type)
def plot_generator(directory, plot_dir, multiple=0):
    with open(directory+"/"+"rounds.csv", 'r') as data:
        plotter(data, "rounds", 4, 5, plot_dir+"/rounds")
    with open(directory + "/" + "agent.csv", 'r') as data:
        plotter(data, "agents", 1, 2, plot_dir+"/agents")


def plotter(data, name, x_index, y_start, plot_dir):
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    csv_object = csv.reader(data, delimiter=',')
    a = next(csv_object)
    plot_type = "line"
    x = []
    y = []
    plt.figure(figsize=(20, 12))
    for col in range(y_start, len(a)):
        x.clear()
        y.clear()
        for row in csv_object:
            if plot_type == "line":
                x.append(int(row[x_index]))
            elif plot_type == "bar":
                x.append(str(row[x_index]))
            if row[col] != "nan":
                y.append(int(float(row[col])))
            else:
                y.append(np.nan)
        if plot_type == "line":
            plt.plot(x, y)
        elif plot_type == "bar":
            plt.bar(x, y, align='edge', width=0.5)
        plt.xlabel(a[x_index])
        plt.xticks(rotation=45)
        plt.ylabel(a[col])
        plt.savefig(plot_dir + '/' + name + '_' + a[col] + '.png')
        plt.clf()
        data.seek(0)
        plot = csv.reader(data, delimiter=',')
        next(plot)

#plot_generator("all_aggregates.csv", "../outputs/multiple/working_multi_layer_2020-02-29_14:34:1_leader_coating", 4,0, "Multi_Layer: 60 Particles", "bar")