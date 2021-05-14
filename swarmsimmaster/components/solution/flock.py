import numpy as np
DEFAULTS = {"flock_rad" : 20, "flock_vel" : 5, "collision_rad" : 0.8, "csv_mid" : "custom"}
VELOCITY_CAP = 30
CAPPED_VELS = True
TIMESTEP= 0.1 #Approximation of a slotframe

def solution(world):
    if not world.network_formed:
        return

    net_id_map = world.net_id_map
    inv_net_id_map = {v : k for k, v in net_id_map.items()}
    for agent in world.get_agent_list():
        set_vel = net_id_map[0] == agent.id
        follow = leader_agent_move(agent, world, True)
        if set_vel and follow:
            continue

        R_COLLISION, R_CONNECTION = .8, float(world.config_data.flock_rad)
        R1, R2 = R_COLLISION, R_CONNECTION
        k_col, k_conn = R1 * R1 + R2, R2

        # set agent control inputs
        vx, vy, vz = 0, 0, 0
        for (net_id, neighbor) in agent.neighbors.items():  # NOTE: currently updated at the end of each slotframe
            agent_id = net_id_map[net_id]
            if agent_id == agent.id:
                continue

            x1, y1, _ = agent.coordinates

            x2, y2 = neighbor
            x1 = float(x1)
            x2 = float(x2)
            y1 = float(y1)
            y2 = float(y2)

            dist = np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
            scaling = 1
            if net_id == 0:
                scaling = float(max(1, len(agent.world.get_agent_list()) / 10))  # NOTE: magic number boo

            vx += 2 * scaling * (x1 - x2) * (
                    k_conn * np.exp((dist) / (R2 * R2)) / (R2 * R2) -
                    k_col * np.exp(-(dist) / (R1 * R1)) / (R1 * R1)
            )
            vy += 2 * scaling * (y1 - y2) * (
                    k_conn * np.exp((dist) / (R2 * R2)) / (R2 * R2) -
                    k_col * np.exp(-(dist) / (R1 * R1)) / (R1 * R1)
            )
            vz += 0

            if not agent.world.config_data.follow_the_leader:
                vx1, vy1, _ = agent.velocities
                vx2, vy2, _ = agent.world.agent_map_id[agent_id].velocities

                vx += (vx1 - vx2)
                vy += (vy1 - vy2)

        print(f"[Mote {inv_net_id_map[agent.id]}] {agent.neighbors} new vels {vx} {vy}", end="\r")
        agent.set_velocities((-vx, -vy, -vz))
        agent.neighbors = []

    for agent in world.get_agent_list():
        agent.move()


def leader_agent_move(agent, world, set_vel=True):  # TODO: how to do follow the leader without a path bias???
    # round = self.world.get_actual_round()
    scale = world.config_data.flock_vel
    set_velocities = lambda vels: agent.set_velocities(vels) if set_vel else None
    set_velocities((scale, 0, 0))  # TODO: iterate over different angles rather than just straight
    return True