from typing import Tuple, List
import copy
import numpy as np
from overcooked.utils import *
from opencooking.utils.world import World
from opencooking.utils.core import *
from opencooking.misc.game.gameimage import GameImage
from opencooking.envs.overcooked_environment import OvercookedEnvironment
from collections import namedtuple


CollisionRepr = namedtuple("CollisionRepr", "time agent_names agent_locations")

OPEN_DIVIDER_SALAD =   [[1, 1, 1, 1, 1, 1, 1],
                        [1, 0, 0, 0, 0, 0, 1],
                        [1, 0, 0, 0, 0, 0, 1],
                        [1, 0, 0, 0, 0, 0, 1],
                        [1, 0, 0, 0, 0, 0, 1],
                        [1, 0, 0, 0, 0, 0, 1],
                        [1, 1, 1, 1, 1, 1, 1]]
OPEN_DIVIDER_SALAD = np.transpose(OPEN_DIVIDER_SALAD)

OPEN_DIVIDER_SALAD_L =  [[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]]
OPEN_DIVIDER_SALAD_L = np.transpose(OPEN_DIVIDER_SALAD_L)

PARTIAL_DEVIDER_SALAD =[[1, 1, 1, 1, 1, 1, 1],
                        [1, 0, 0, 1, 0, 0, 1],
                        [1, 0, 0, 1, 0, 0, 1],
                        [1, 0, 0, 1, 0, 0, 1],
                        [1, 0, 0, 1, 0, 0, 1],
                        [1, 0, 0, 0, 0, 0, 1],
                        [1, 1, 1, 1, 1, 1, 1]]
PARTIAL_DEVIDER_SALAD = np.transpose(PARTIAL_DEVIDER_SALAD)

PARTIAL_DEVIDER_SALAD_L =  [[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                        [1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1],
                        [1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1],
                        [1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1],
                        [1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1],
                        [1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1],
                        [1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1],
                        [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1],
                        [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1],
                        [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1],
                        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]]
PARTIAL_DEVIDER_SALAD_L = np.transpose(PARTIAL_DEVIDER_SALAD_L)

FULL_DIVIDER_SALAD =   [[1, 1, 1, 1, 1, 1, 1],
                        [1, 0, 0, 1, 0, 0, 1],
                        [1, 0, 0, 1, 0, 0, 1],
                        [1, 0, 0, 1, 0, 0, 1],
                        [1, 0, 0, 1, 0, 0, 1],
                        [1, 0, 0, 1, 0, 0, 1],
                        [1, 1, 1, 1, 1, 1, 1]]
FULL_DIVIDER_SALAD = np.transpose(FULL_DIVIDER_SALAD)

# x, y
ITEM_LOCATIONS = {
    "tomato": (5, 0),
    "lettuce": (6, 1),
    "cutboard0": (0, 1),
    "cutboard1": (0, 2),
    "plate0": (5, 6),
    "plate1": (6, 5),

    "counter0": (3, 1),
    "counter1": (3, 2),
    "counter2": (3, 3),
    "counter3": (3, 4),

    "star": (0, 3)
}

ITEM_LOCATIONS_L = {
    "tomato": (12, 0),
    "lettuce": (13, 1),
    "cutboard0": (0, 1),
    "cutboard1": (0, 2),
    "plate0": (12, 10),
    "plate1": (13, 9),

    "counter0": (6, 6),
    "counter1": (6, 7),
    "counter2": (6, 8),
    "counter3": (6, 9),

    "star": (0, 9)
}

MOVABLES = ["tomato", "lettuce", "plate0", "plate1"]


def identify_items_at(location: Tuple[int, int], item_locations: dict) -> List[str]:
    result = []
    for item, loc in item_locations.items():
        if (loc[0] == location[0]) and (loc[1] == location[1]):
            result.append(item)
    return result


def get_dst_tuple(item: str, level: list, item_locations: dict) -> Tuple[Tuple[int, int], list]:
    destination: Tuple[int, int] = item_locations[item]
    level: list = copy.deepcopy(level)
    level[destination[0]][destination[1]] = 0
    return destination, level


class GPTWorld(World):
    NAV_ACTIONS = [(0, 1), (0, -1), (-1, 0), (1, 0)]
    def __init__(self, arglist):
        super().__init__(arglist)

    def get_gridsquare_list_at(self, location) -> list:
        gss = list(filter(lambda o: o.location == location, self.get_object_list()))
        assert len(gss) > 0, "{} gridsquares at {}: {}".format(len(gss), location, gss)
        return gss
    

class OvercookedEnvGPT(OvercookedEnvironment):
    def __init__(self, num_agents, level, arglist):
        super().__init__(num_agents, level, arglist)

    def reset(self):
        self.world = GPTWorld(arglist=self.arglist)
        self.recipes = []
        self.sim_agents = []
        self.agent_actions = {}
        self.t = 0
        # For visualizing episode.
        self.rep = []
        # For tracking data during an episode.
        self.collisions = []
        self.termination_info = ""
        self.successful = False
        # Load world & distances.
        self.load_level(
                level=self.level,
                num_agents=self.num_agents)
        self.all_subtasks = self.run_recipes()
        self.world.make_loc_to_gridsquare()
        self.world.make_reachability_graph()
        self.cache_distances()
        self.obs_tm1 = copy.copy(self)

        if self.arglist.record or self.arglist.with_image_obs:
            self.game = GameImage(
                    filename=self.filename,
                    world=self.world,
                    sim_agents=self.sim_agents,
                    record=self.arglist.record)
            self.game.on_init()
            if self.arglist.record:
                self.game.save_image_obs(self.t)
        return copy.copy(self)
    
    def step(self, action_dict):
        # Track internal environment info.
        self.t += 1
        print("===============================")
        print("[environment.step] @ TIMESTEP {}".format(self.t))
        print("===============================")
        # Get actions.
        for sim_agent in self.sim_agents:
            sim_agent.action = action_dict[sim_agent.name]
        # Check collisions.
        self.check_collisions()
        self.obs_tm1 = copy.copy(self)
        # Execute.
        agents_states = self.execute_navigation()
        for agent_ in self.sim_agents:
            agents_states[agent_.name]['loc'] = agent_.location
        # Visualize.
        self.display()
        self.print_agents()
        if self.arglist.record:
            self.game.save_image_obs(self.t)
        # Get a plan-representation observation.
        new_obs = copy.copy(self)
        # Get an image observation
        image_obs = self.game.get_image_obs()

        done = self.done()
        reward = self.reward()
        info = {"t": self.t, "obs": new_obs,
                "image_obs": image_obs,
                "done": done, "termination_info": self.termination_info, "agents_states": agents_states}
        return new_obs, reward, done, info
    
    def execute_navigation(self):
        agents_states = {}
        for agent in self.sim_agents:
            action_str, action_loc = interact(agent=agent, world=self.world)
            agents_states[agent.name] = {'action_str': action_str, 'action_loc': action_loc} 
            self.agent_actions[agent.name] = agent.action
        return agents_states
