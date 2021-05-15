# Description of Scenarios
The scenarios determine the initialization of the robotic task, and can relate to the goal of the task or environment as well.

- `6tisch_scenario.py`: used for initializing networks. Reads an argument list that gives a list of agent positions. The 6TiSCH simulator uses this object to determine starting locations in SwarmSim.
- `agent_item_location.py`: example for adding interactive items into the SwarmSim dynamics. Spawns only one agent.
- `agents_items_locations_ring.py`: multiple items and agents of 'agent_item_location'. 
- `formation_ctrl`: randomly initialize agents in a disc of configurable radius. This scenario is used by all of the flocking solutions (`formation_circ, formation_line`), and handles some decentralized agent communication for control. 
- `lonely_agent.py`: adds only three nearby agents for debugging control and communications solutions.
- `n_agent_in_line.py`: initializes a number of agents along the y-axis of the world, uniformly distributed.
- `post_viz.py`: UNDER CONSTRUCTION, used for rendering simulations from logged data.
- `test_interfaces.py`: original SwarmSim scenario for testing the interface between agents and other objects.
