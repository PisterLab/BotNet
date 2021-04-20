from stable_baselines3.common.env_checker import  check_env
from swarmsim_env import SingleExplorer

print(check_env(SingleExplorer()))
