import matplotlib.pyplot as plt
import os
import numpy as np

ALL_MODELS = ["full", "disk", "friis_upper", "friis_average", "friis_lower", "pister_hack"]

for model in ALL_MODELS:
    data_dir = "logs/" + model + "_100"
    data = []
    for f in os.listdir(data_dir):
        x = np.load(data_dir + "/" + f)
        data.append(x)
    data = np.array(data)
    print(np.mean(data, axis=0))

#
# x_pos = [i for i, _ in enumerate(x)]
#
# plt.bar(x_pos, energy, color='green')
# plt.xlabel("Energy Source")
# plt.ylabel("Energy Output (GJ)")
# plt.title("Energy output from various fuel sources")
#
# plt.xticks(x_pos, x)
#
# plt.show()