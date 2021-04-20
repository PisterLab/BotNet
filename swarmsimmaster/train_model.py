import gym
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3 import PPO
from stable_baselines3.ppo import MlpPolicy
from stable_baselines3.common.evaluation import evaluate_policy
from swarmsim_env import SingleExplorer
from eval_callback import Eval
from stable_baselines3.common import results_plotter
#print("hello")
#log_dir = "logs/"
env =  SingleExplorer()
model = PPO(MlpPolicy, env, verbose=0)
model.learn(total_timesteps=20000, callback=Eval)
print("trained")
#rew, std = evaluate_policy(model, env)
#print("reward = %f , std = %f" %(rew, std))
#model.learn(total_timesteps=10000, callback=Eval)
#rew, std = evaluate_policy(model, env)
#print("reward = %f , std = %f" %(rew, std))
#results_plotter.plot_results([log_dir], 10000, 'timesteps', "pls_learn")
model.save("models/ppo_search")



