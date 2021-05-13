# BotNet: A Simulator for Studying the Effects of Accurate Communication Models on High-agent Count Multi-agent Control

Contents:
1. Setup and Background
2. Running BotNet and Experiments
3. File Structure Explanations

----
## Setup and Background:
This framework runs entirely on python and has very few requirements.
```
<set up your own virtualenv with conda or whatever>
pip install -r requirements.txt
cd swarmsimmaster/
```


### SwarmSim: Multi-agent Control and Swarm vs. Swarm Games
In this work we build off of [Swarm-Sim](https://gitlab.cs.uni-duesseldorf.de/cheraghi/swarm-sim): A 2D & 3D Simulation Core for Swarm Agents. Some notable changes have been made over the original version.
* Bugs were fixed causing the simulator to crash in routine operations.
* Adding a framework for continuous robotic control (discrete agent movements were default).
* More scenarios for studying multi-agent control
* Created a wrapper class for remote control of the simulator
* Added functionality to pass arguments into scenarios. 

Swarm-Sim comprosises the dynamics simulation componenet of the dual-simulator. There are two primary places where experiments are defined on the Swarm-Sim side. 
#### Scenarios
A scenario is the initial conditions for a simulation. In these files, the world api is used to define the initial positions of all objects in the simulation. Scenarios are loaded from swarmsimmaster/components/scenarios at the beggining of the simulation. The current simulation to be loaded is defined in swarmsimmaster/config.ini

#### Solutions.  
Solutions are where control updates are implemented. These use utilize the world api to define the simulation behavior at every time step. The solution function is called on every iteration of Swarm-Sim's main loop. Like a scenario a solution is loaded from swarmsimmaster/components/solutions and an experiments solution is defined in config.ini. See swarmsimmaster/components/solutions/flock.py for an example solution
----
## Running BotNet
to run the dual visualization, first (in the top level directory): python dual_vis_messenger_server.py  then (in seperate terminals). 6tisch/gui/backend/start and (in the swarmsimmaster folder) python3 swarmsim.py

We have included a bash script for running the code. To use it, enter the following in your terminal.
```
./run.sh
```

fix below 
### BotNet RPC server:
To start the rpc server cd into the swarmsimmaster directory and run `python3 rpyc_server.py`
Once the server is started you can connect to the via the following python code in any directory  
`import rpyc`  
`service = rpyc.connect("localhost", 18861).root`  
This will let you remotely control the simulator via the service variable.

### SwarmSim Interface
`python swarmsim.py`

`python ../../../6tisch-simulator/bin/runSim.py`

## Examples

#### Flocking

#### Formation Control


----
## BotNet Structure
In this section we detail the structure of the simulator and what new users should know when designing new experiments.

#### Scenario Initialization:
This is the starting situation for the simulation. A **scenario** describes the initial agent positions as well as their environment. To create a scenario utilize the world API in a Python script located in the scenarios folder. Examples of how to set up scenarios are in the scenarios folder. To run your scenario you must set the scenario argument at the bottom of config.ini to the name of your scenario file. Below is the simplest  example of creating a lonely agent in the center of the world (which can be found [here](https://github.com/PisterLab/BotNet/blob/5af7fc809dea29e6e49b5275df13184c534b6518/gym-swarm-sim/envs/swarmsimmaster/components/scenario/configurable.py)).

```
def scenario(world):
  world.add_agent(world.grid.get_center())
```

For more details on the current scenarios, see the scenario description [readme](./swarmsimmaster/components/scenario/readme.md).
#### Control Solutions:
The solution is where controls and dynamics are implemented. At every step of the main loop the solution is executed. A solution file describes both the controls of the agents and can describe extra dynamics or interactions. Below is a solution which moves every agent in a random direction, which can be found [here](https://github.com/PisterLab/BotNet/blob/72a2253bbeb5b4f1995ab12eae9a9c672c55892d/gym-swarm-sim/envs/swarmsimmaster/components/solution/random_walk.py). 

```
def solution(world):
  if world.get_actual_round() % 1 == 0:
    for agent in world.get_agent_list():
      agent.move_to(random.choice(world.grid.get_directions_list()))
```
Config.ini can be used t set all arguments for the simulation. These include which grid world to use. Whether to use an agent with 0th 1st or 2nd order dynamics, how big the world is, etc. 

##### Agent Level Control
How to write controls at the agent level:
* In core, create a new python file with a class that inherits from agent.py
* Define an instance method in this agent to describe control eg. move(self). . .
* Pass the agent class in as the new_class parameter when adding the agent in the world
* Simply call the move function in the solution


### 6TiSCH + Swarm Sim: Networked Multi-Agent Control (No RPC & Real-time Viz)
The 6TiSCH simulator can be seamlessly integrated to validate control performance with different local communications models. This tool can also be used by networking researchers to add more complex schedule functions and network behavior.

Running Google Doc: https://docs.google.com/document/d/1OhyHHBxHN3_bAwsYYcrqfswcTrh-pLQrN6X59aoQMSg/edit?usp=sharing

----

=======
## Running the code

### BotNet RPC server:
To start the rpc server cd into the swarmsimmaster directory and run `python3 rpyc_server.py`
Once the server is started you can connect to the via the following python code in any directory  
`import rpyc`  
`service = rpyc.connect("localhost", 18861).root`  
This will let you remotely control the simulator via the service variable.

### SwarmSim Interface
`python swarmsim.py`

`python ../../../6tisch-simulator/bin/runSim.py`


### Visualizing both Simulators

Both simulators can be visualized live in the same experiment. To do this 
1. Set the Swarm Sim scenario to dual_vis_tisch
2. Set the Swarm sim solution to tisch_visualization
3. run dual_visualization.sh
----

## Examples

#### Flocking

#### Formation Control

## Citation
To cite this work, please use the following (_we can upload to arxiv so everything is good to go_):
```
@article{botnet2021,
  Title = {BotNet: A Simulator for Studying the Effects of Accurate Communication Models on High-agent Count Multi-agent Control},
  Author = {Felipe Campos, Nathan Lambert, Mark Selden, Jason Zhou, Daniel Drew, Kristofer S. J. Pister},
  journal={To Appear},
  year={2021}
}
```
