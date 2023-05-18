from typing import List, Tuple
import os
from overcooked.utils import *
from overcooked.env import *
from opencooking.utils.utils import *
import openai


# Reference:
# https://github.com/openai/openai-cookbook/blob/main/examples/How_to_format_inputs_to_ChatGPT_models.ipynb
class ChatBot:
    def __init__(self, num_agents: int, config: dict, arglist):
        if not("openai_api_key" in os.environ):
            openai.api_key = config["common"]["openai_api_key"]
        self.model: str = config["common"]["openai_model"]
        self.messages: list = []

        instruction, example = None, None
        self.num_agents: int = num_agents
        if self.num_agents == 1:
            with open("utils/chatgpt/single_agent_instruction.txt", "r") as f:
                instruction = f.read()
            with open("utils/chatgpt/single_agent_example.txt", "r") as f:
                example = f.read()
        elif self.num_agents == 2:
            instruction = ocma_instruction
            example = ocma_example
        else:
            assert False, f"num_agents must be 1 or 2: {self.num_agents}"

        self.messages.append({"role": "system", "content": "You are a Python programmer. Help me write code in Python."})
        self.messages.append({"role": "user", "content": instruction})

        # one-shot learning
        self.messages.append({
            "role": "system",
            "name": "example_user",
            "content": "Make a lettuce salad."
        })
        self.messages.append({"role": "system", "name": "example_assistant", "content": example})

    def __call__(self, message):
        self.messages.append({"role": "user", "content": message})
        result: str = self.execute()
        print(result)
        self.messages.append({"role": "assistant", "content": result})
        return result

    def execute(self) -> str:
        try:
            completion = openai.ChatCompletion.create(model=self.model, messages=self.messages)
            #print(completion.usage) # number of tokens consumed
            return completion.choices[0].message.content
        except Exception as e:
            print(e)
            return colors.RED + f"ERROR: {e}" + colors.ENDC


class GPTWorld(World):
    NAV_ACTIONS = [(0, 1), (0, -1), (-1, 0), (1, 0)]
    def __init__(self, arglist):
        super().__init__(arglist)

    def get_gridsquare_list_at(self, location) -> list:
        gss = list(filter(lambda o: o.location == location, self.get_object_list()))
        assert len(gss) > 0, "{} gridsquares at {}: {}".format(len(gss), location, gss)
        return gss


class GPTAgent:
    def __init__(self, id: int, level: str, arglist):
        assert 0 <= id <= 4
        self.id = id
        self.location = None
        self.on_hand = None
        self.level = None
        self.item_locations = ITEM_LOCATIONS
        self.history = []
        self.prev_state = None
        global g_max_steps
        if level == "open-divider_salad":
            self.level = OPEN_DIVIDER_SALAD
        elif level == "open-divider_salad_large":
            self.level = OPEN_DIVIDER_SALAD_L
            self.item_locations = ITEM_LOCATIONS_L
            g_max_steps = 200
        elif level == "partial-divider_salad":
            self.level = PARTIAL_DEVIDER_SALAD
        elif level == "partial-divider_salad_large":
            self.level = PARTIAL_DEVIDER_SALAD_L
            self.item_locations = ITEM_LOCATIONS_L
            g_max_steps = 200
        elif level == "full-divider_salad":
            self.level = FULL_DIVIDER_SALAD
        else:
            assert False, f"unknown level: {arglist.level}"

    def set_state(self, location: Tuple[int, int], action_str: str, action_loc: Tuple[int, int]):
        """ set the latest game state
        Args:
            location (Tuple[int, int]): agent's current location
            action_str (str): action taken by the agent
            action_loc (Tuple[int, int]): location where the action was taken
        """
        self.location = location
        if action_str is None:
            return
        if self.prev_state is not None:
            # discard duplicate state
            if (self.prev_state[0] == location) and (self.prev_state[1] == action_str) and (self.prev_state[2] == action_loc):
                return
        description = action_str
        items: List[str] = identify_items_at(action_loc, self.item_locations)
        if len(items) > 0:
            # remove duplicated items
            if ("sliced" in description) or ("picked" in description):
                if "tomato" in description:
                    items.remove("tomato")
                if "lettuce" in description:
                    items.remove("lettuce")
                if ("picked" in description) and (len(items) > 0):
                    description += " from"
            # change description for merged plate
            elif ("merged plate" in description) and (self.on_hand is not None):
                description = "put sliced " + ", ".join(self.on_hand) + " onto"
            description += ' ' + ", ".join(items)
            print(colors.GREEN + f"agent{self.id}.set_state(): " + description + colors.ENDC)
        self.history.append(description)
        if "picked" in description:
            # identify what item was picked up
            for item in self.item_locations.keys():
                if (item in description) and (item in MOVABLES):
                    if self.on_hand is None:
                        self.on_hand = [item]
                    else:
                        self.on_hand.append(item)
        elif ("put" in description) or ("merged" in description):
            if self.on_hand is not None:
                # update the location of the item
                for item in MOVABLES:
                    for obj in self.on_hand:
                        if item in obj:
                            self.item_locations[item] = action_loc
                self.on_hand = None
        if self.on_hand is not None:
            print(colors.YELLOW + f"agent{self.id}.on_hand = {self.on_hand}" + colors.ENDC)
        self.prev_state = (location, action_str, action_loc)

    def reset_state(self, reset_on_hand: bool=False):
        """ reset the game state of the agent
        Args:
            reset_on_hand (bool, optional): reset the on_hand variable. Defaults to False.
        """
        self.location = None
        self.action_str = None
        self.action_loc = None
        if reset_on_hand:
            self.on_hand = None

    def move_to(self, destination: Tuple[int, int]) -> bool:
        """ move to the specified destination
        Args:
            destination (Tuple[int, int]): 2D coordinate of the destination
        Returns:
            bool: True when the agent has reached the destination
        """
        act = (0, 0)
        if not isinstance(destination, tuple):
            print(colors.RED + f"ERROR: destination is not a tuple: {destination}" + colors.ENDC)
            return False, act
        if self.__has_reached(destination):
            print(colors.YELLOW + f"agent{self.id}.move_to(): reached destination" + colors.ENDC)
            return True, act
        dx = destination[0] - self.location[0]
        dy = destination[1] - self.location[1]
        print(colors.YELLOW + f"agent{self.id}.move_to(): source={self.location}, destination={destination}, (dx, dy) = ({dx}, {dy})" + colors.ENDC)
        global g_keyboard
        if dx < 0:
            """
            g_keyboard.press(Key.left)
            g_keyboard.release(Key.left)
            """
            return False, (-1, 0)
        elif dx > 0:
            """
            g_keyboard.press(Key.right)
            g_keyboard.release(Key.right)
            """
            return False, (1, 0)
        if dy < 0:
            """
            g_keyboard.press(Key.up)
            g_keyboard.release(Key.up)
            """
            return False, (0, -1)
        elif dy > 0:
            """
            g_keyboard.press(Key.down)
            g_keyboard.release(Key.down)
            """
            return False, (0, 1)

    def fetch(self, item: str) -> bool:
        """ move to the item's location and pick it up
        Args:
            item (str): item to be picked up
        Returns:
            bool: success or failure
        """
        act = (0, 0)
        if self.on_hand is not None:
            for obj in self.on_hand:
                if item in obj:
                    return True, act  # item is already in hand
        for key in self.item_locations.keys():
            if item == key:
                destination, level = get_dst_tuple(item, self.level, self.item_locations)
                path: List[Tuple[int, int]] = find_path(self.location, destination, level)
                print(colors.YELLOW + f"agent{self.id}.fetch(): path={path}" + colors.ENDC)
                _, act = self.move_to(path[1])
                break
        return False, act

    def put_onto(self, item) -> bool:
        """ place the object in hand onto the specified item
        Args:
            item (str or Tuple[int, int]): where to put the object
        Returns:
            bool: True if the task is closed
        """
        act = (0, 0)
        if self.on_hand is None:
            #print(colors.RED + f"GPTAgent.put_onto(): nothing in hand to put" + colors.ENDC)
            return True, act
        destination, level = None, None
        if isinstance(item, str):
            if not(item in self.item_locations.keys()):
                print(colors.RED + f"agent{self.id}.put_onto(): invalid item: {item}" + colors.ENDC)
                return True, act
            destination, level = get_dst_tuple(item, self.level, self.item_locations)
        elif isinstance(item, tuple):
            pass #TODO: also accept 2D coordinate
        else:
            assert False, f"item must be str or Tuple[int, int]: {type(item)}"
        path: List[Tuple[int, int]] = find_path(self.location, destination, level)
        print(colors.YELLOW + f"agent{self.id}.put_onto(): path={path}" + colors.ENDC)
        _, act = self.move_to(path[1])
        return False, act

    def slice_on(self, item: str) -> bool:
        """ slice food at the specified item's location
        Args:
            item (str): the name of the item to chop on (must be a cutboard)
        Returns:
            bool: True if the task is closed
        """
        act = (0, 0)
        if not(item in self.item_locations.keys()):
            print(colors.RED + f"agent{self.id}.slice_on(): invalid item: {item}" + colors.ENDC)
            return True, act
        if not("cutboard" in item):
            print(colors.RED + f"agent{self.id}.slice_on(): cannot slice on {item}" + colors.ENDC)
            return True, act
        destination: Tuple[int, int] = self.item_locations[item]
        for description in self.history[::-1]:
            if ("put" in description) and (item in description):
                _, act = self.move_to(destination)
                break
            elif "sliced" in description:
                return True, act
        return False, act

    def deliver(self, dummy=None) -> bool:
        """ deliver the food to the goal destination (i.e., "star")
        Args:
            dummy (_type_, optional): ignored
        Returns:
            bool: True if the task is closed
        """
        act = (0, 0)
        destination = list(self.item_locations["star"])
        destination[0] += 1
        #self.move_to(tuple(destination)):
        flag, act = self.move_to(tuple(destination))
        if flag:
            return flag, (-1, 0)
        return flag, act

    def __has_reached(self, destination) -> bool:
        return (self.location[0] == destination[0]) and (self.location[1] == destination[1])