import gym
from stable_baselines.common.policies import MlpPolicy
from stable_baselines.common.vec_env import DummyVecEnv
from stable_baselines import ACER
from swarmsim_env import SwarmSimEnvSingle
env = DummyVecEnv([lambda : SwarmSimEnvSingle()])
model = ACER(MlpPolicy, env, verbose=1)
model.learn(total_timesteps=1000)
