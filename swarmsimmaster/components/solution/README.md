# Description of Solutions

Solutions determine the control behavior for each agent.
- `create_delete.py`: This solution is an example for creating and deleting, agents, items or locations.
- `flock.py`: Core logic for follow-the-leader and emergent flocking.
- `formation_circ.py`: Decentralized circle formation controller.
- `formation_line.py`: Decentralized line formation controller.
- `marking_3d_global.py`: Annotating SwarmSim 3D world example, can be used for search applications and other tools.
- `marking_3d_local.py`: See above and original SwarmSim paper for more.
- `marking_3d_noComm.py`: See above and original SwarmSim paper for more.
- `post_viz.py`: UNDER CONSTRUCTION, for visualizing results on logged data.
- `random_walk.py`: Random walk all agents.
- `random_walk_with_take_and_drop.py`: Random walk all agents and collect matter if encountered.
- `rl_model.py`: UNDER CONSTRUCTION, interface for running trained RL model from stable_baselines3.
- `scanning_for_all_aims.py`: This solution just scans for agents that are within 5 meters.
- `test_all_the_interfaces.py`: This solution tests all the interfaces (e.g. agent-matter) that are provided from the world.
- `test_marking.py`: A test for annotating the world.
- `test_velo_agent.py`: A test for our base agent that takes velocity commands (original SwarmSim agents only took position commands).
- `tisch_visualization.py`: Solution for using full dual visualization of both simulators.
