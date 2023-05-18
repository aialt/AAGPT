import numpy as np
from typing import Tuple, List
import random
import re
from opencooking.utils.core import *
from opencooking.utils.utils import *


class colors:
    RED = "\033[31m"
    ENDC = "\033[m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"


def fix_seed(seed):
    np.random.seed(seed)
    random.seed(seed)


def __extract_object_names(s: str) -> str:
    result = []
    if "Tomato" in s:
        result.append("tomato")
    if "Lettuce" in s:
        result.append("lettuce")
    if "Plate" in s:
        result.append("plate")
    return ", ".join(result)


def interact(agent, world) -> Tuple[str, Tuple[int, int]]:
    """Carries out interaction for this agent taking this action in this world.

    The action that needs to be executed is stored in `agent.action`.
    """

    action_str = None
    action_loc = None

    # agent does nothing (i.e. no arrow key)
    if agent.action == (0, 0):
        return action_str, action_loc

    action_loc = world.inbounds(tuple(np.asarray(agent.location) + np.asarray(agent.action)))
    gs = world.get_gridsquare_at(action_loc)

    # if floor in front --> move to that square
    if isinstance(gs, Floor): #and gs.holding is None:
        action_str = "moved to"
        agent.move_to(gs.location)

    # if holding something
    elif agent.holding is not None:
        # not None only when agent puts foods on cutboard or plate, or delivers

        # if delivery in front --> deliver
        if isinstance(gs, Delivery):
            obj = agent.holding
            #print(f"holding && delivering: obj.contents = {obj.contents}")

            if obj.is_deliverable():
                action_str = f"delivered {__extract_object_names(str(obj.contents))} at"
                gs.acquire(obj)
                agent.release()
                print('\nDelivered {}!'.format(obj.full_name))

        # if occupied gridsquare in front --> try merging
        elif world.is_occupied(gs.location):
            # Get object on gridsquare/counter
            obj = world.get_object_at(gs.location, None, find_held_objects = False)
            #print(f"holding && occupied: obj.contents = {obj.contents}")

            if mergeable(agent.holding, obj):
                action_str = f"merged {__extract_object_names(str(obj.contents))} with"
                world.remove(obj)
                o = gs.release() # agent is holding object
                world.remove(agent.holding)
                agent.acquire(obj)
                world.insert(agent.holding)
                # if playable version, merge onto counter first
                if world.arglist.gpt:
                    # --gpt
                    gs.acquire(agent.holding)
                    agent.release()

        # if holding something, empty gridsquare in front --> chop or drop
        elif not world.is_occupied(gs.location):
            obj = agent.holding
            #print(f"holding && not(occupied): obj.contents = {obj.contents}")

            if isinstance(gs, Cutboard) and obj.needs_chopped() and not world.arglist.gpt:
                # normally chop, but if in playable game mode then put down first
                obj.chop()
            else:
                # --gpt
                action_str = f"put {__extract_object_names(str(obj.contents))} onto"
                gs.acquire(obj) # obj is put onto gridsquare
                agent.release()
                assert world.get_object_at(gs.location, obj, find_held_objects =\
                    False).is_held == False, "Verifying put down works"

    # if not holding anything
    elif agent.holding is None:
        # not empty in front --> pick up
        if world.is_occupied(gs.location) and not isinstance(gs, Delivery):
            obj = world.get_object_at(gs.location, None, find_held_objects = False)
            #print(f"not(holding) && occupied: obj.contents = {obj.contents}")

            # if in playable game mode, then chop raw items on cutting board
            if isinstance(gs, Cutboard) and obj.needs_chopped() and world.arglist.gpt:
                # --gpt
                action_str = f"sliced {__extract_object_names(str(obj.contents))} on"
                obj.chop()
            else:
                action_str = f"picked up {__extract_object_names(str(obj.contents))}"
                gs.release()
                agent.acquire(obj)

        # if empty in front --> interact
        elif not world.is_occupied(gs.location):
            pass

    return action_str, action_loc


def index_2d(data, search):
    for i, e in enumerate(data):
        try:
            return i, e.index(search)
        except ValueError:
            pass
    raise ValueError("{!r} is not in list".format(search))


def find_path(start: Tuple[int, int], end: Tuple[int, int], level: list, cost: int=1) -> List[Tuple[int, int]]:
    path = search(level, cost, start, end)
    #print(path, type(path))
    print('\n'.join([''.join([colors.GREEN + "{:" ">3d}".format(item) + colors.ENDC if item >=0 else\
                               "{:" ">3d}".format(item) for item in row]) for row in np.transpose(path)]))
    result = []
    i = 0
    while True:
        try:
            position = index_2d(path, i)
        except ValueError:
            break
        result.append(position)
        i += 1
    return result


# Reference:
# https://github.com/BaijayantaRoy/Medium-Article/blob/master/A_Star.ipynb
class Node:
    """
        A node class for A* Pathfinding
        parent is parent of the current Node
        position is current position of the Node in the maze
        g is cost from start to current Node
        h is heuristic based estimated cost for current Node to end Node
        f is total cost of present node i.e. :  f = g + h
    """

    def __init__(self, parent=None, position=None):
        self.parent = parent
        self.position = position

        self.g = 0
        self.h = 0
        self.f = 0
    def __eq__(self, other):
        return self.position == other.position


#This function return the path of the search
def return_path(current_node,maze):
    path = []
    no_rows, no_columns = np.shape(maze)
    # here we create the initialized result maze with -1 in every position
    result = [[-1 for i in range(no_columns)] for j in range(no_rows)]
    current = current_node
    while current is not None:
        path.append(current.position)
        current = current.parent
    # Return reversed path as we need to show from start to end path
    path = path[::-1]
    start_value = 0
    # we update the path of start to end found by A-star serch with every step incremented by 1
    for i in range(len(path)):
        result[path[i][0]][path[i][1]] = start_value
        start_value += 1
    return result


def search(maze, cost, start, end):
    """
        Returns a list of tuples as a path from the given start to the given end in the given maze
        :param maze:
        :param cost
        :param start:
        :param end:
        :return:
    """

    # Create start and end node with initized values for g, h and f
    start_node = Node(None, tuple(start))
    start_node.g = start_node.h = start_node.f = 0
    end_node = Node(None, tuple(end))
    end_node.g = end_node.h = end_node.f = 0

    # Initialize both yet_to_visit and visited list
    # in this list we will put all node that are yet_to_visit for exploration.
    # From here we will find the lowest cost node to expand next
    yet_to_visit_list = []
    # in this list we will put all node those already explored so that we don't explore it again
    visited_list = []

    # Add the start node
    yet_to_visit_list.append(start_node)

    # Adding a stop condition. This is to avoid any infinite loop and stop
    # execution after some reasonable number of steps
    outer_iterations = 0
    max_iterations = (len(maze) // 2) ** 10

    # what squares do we search . serarch movement is left-right-top-bottom
    #(4 movements) from every positon

    move  =  [[-1, 0 ], # go up
              [ 0, -1], # go left
              [ 1, 0 ], # go down
              [ 0, 1 ]] # go right

    """
        1) We first get the current node by comparing all f cost and selecting the lowest cost node for further expansion
        2) Check max iteration reached or not . Set a message and stop execution
        3) Remove the selected node from yet_to_visit list and add this node to visited list
        4) Perofmr Goal test and return the path else perform below steps
        5) For selected node find out all children (use move to find children)
            a) get the current postion for the selected node (this becomes parent node for the children)
            b) check if a valid position exist (boundary will make few nodes invalid)
            c) if any node is a wall then ignore that
            d) add to valid children node list for the selected parent

            For all the children node
                a) if child in visited list then ignore it and try next node
                b) calculate child node g, h and f values
                c) if child in yet_to_visit list then ignore it
                d) else move the child to yet_to_visit list
    """
    #find maze has got how many rows and columns
    no_rows, no_columns = np.shape(maze)

    # Loop until you find the end

    while len(yet_to_visit_list) > 0:

        # Every time any node is referred from yet_to_visit list, counter of limit operation incremented
        outer_iterations += 1

        # Get the current node
        current_node = yet_to_visit_list[0]
        current_index = 0
        for index, item in enumerate(yet_to_visit_list):
            if item.f < current_node.f:
                current_node = item
                current_index = index

        # if we hit this point return the path such as it may be no solution or
        # computation cost is too high
        if outer_iterations > max_iterations:
            print ("giving up on pathfinding too many iterations")
            return return_path(current_node,maze)

        # Pop current node out off yet_to_visit list, add to visited list
        yet_to_visit_list.pop(current_index)
        visited_list.append(current_node)

        # test if goal is reached or not, if yes then return the path
        if current_node == end_node:
            return return_path(current_node,maze)

        # Generate children from all adjacent squares
        children = []

        for new_position in move:

            # Get node position
            node_position = (current_node.position[0] + new_position[0], current_node.position[1] + new_position[1])

            # Make sure within range (check if within maze boundary)
            if (node_position[0] > (no_rows - 1) or
                node_position[0] < 0 or
                node_position[1] > (no_columns -1) or
                node_position[1] < 0):
                continue

            # Make sure walkable terrain
            if maze[node_position[0]][node_position[1]] != 0:
                continue

            # Create new node
            new_node = Node(current_node, node_position)

            # Append
            children.append(new_node)

        # Loop through children
        for child in children:

            # Child is on the visited list (search entire visited list)
            if len([visited_child for visited_child in visited_list if visited_child == child]) > 0:
                continue

            # Create the f, g, and h values
            child.g = current_node.g + cost
            ## Heuristic costs calculated here, this is using eucledian distance
            child.h = (((child.position[0] - end_node.position[0]) ** 2) +
                       ((child.position[1] - end_node.position[1]) ** 2))

            child.f = child.g + child.h

            # Child is already in the yet_to_visit list and g cost is already lower
            if len([i for i in yet_to_visit_list if child == i and child.g > i.g]) > 0:
                continue

            # Add the child to the yet_to_visit list
            yet_to_visit_list.append(child)


__code_block_regex = re.compile(r"```(.*?)```", re.DOTALL)

def __extract_python_code(content: str) -> str:
    global __code_block_regex
    code_blocks: list = __code_block_regex.findall(content)
    if code_blocks:
        full_code = "\n"
        for block in code_blocks:
            if block.startswith("python"):
                full_code += block[7:] + "\n"
            elif block.startswith(" python"):
                full_code += block[8:] + "\n"
            else:
                #pass
                full_code += block[0:] + "\n"
        print(colors.GREEN + "\n=========== execution =============")
        print(full_code)
        print("===================================" + colors.ENDC)
        return full_code
    else:
        return None


def get_task_queue(ws, g_chatbot, agent1, agent2):
    #question = input(colors.GREEN + "Enter a task: " + colors.ENDC)
    task = ws["common"]["task"]
    print("The task: " + task + colors.ENDC)
    print(colors.YELLOW + "ChatGPT: Thinking...please wait..." + colors.ENDC)
    num_retries = 0
    max_retries = 5
    while num_retries < max_retries:
        response: str = g_chatbot(task)
        print("\n-------------------------- response --------------------------")
        print(colors.YELLOW + "ChatGPT: " + colors.ENDC + response)
        code: str = __extract_python_code(response)
        if code is None:
            print(colors.RED + "ERROR: no python code found in the response. Retrying..." + colors.ENDC)
            num_retries += 1
            question = "You must generate valid Python code. Please try again."
            continue
        else:
            if len(code) == 0:
                print(colors.RED + "ERROR: python code is empty. Retrying..." + colors.ENDC)
                num_retries += 1
                question = "You must generate valid Python code. Please try again."
                continue
            else:
                print("\nPlease wait while I execute the above code...")
                try:
                    # existing local vars must be given explicitly as a dict
                    ldict = {"agent1": agent1, "agent2": agent2}
                    exec(code, globals(), ldict)#locals())
                    task_queue = ldict["task_queue"]
                    print("Done executing code.")
                    break
                except Exception as e:
                    print(colors.RED + "ERROR: could not execute the code: {}\nRetrying...".format(e) + colors.ENDC)
                    num_retries += 1
                    question = "While executing your code I've encountered the following error: {}\nPlease fix the error and show me valid code.".format(e)
                    continue
    print("Excecuting the task queue in the simulator...")
    return task_queue


ocma_instruction = """I would like you to help me work with AI agents called "agent1" and "agent2" in a kitchen environment similar to the video game Overcooked.
Inside the kitchen there are the following items: ["tomato", "lettuce", "plate0", "plate1", "cutboard0", "cutboard1", "counter0", "counter1", "counter2", "counter3"].

Each agent has the following functions that you can use to make them take actions:
fetch(item: str) - go to the item's location and pick it up
put_onto(item: str) - put the object in hand onto the item
slice_on(item: str) - slice food (item must be a cutboard)
deliver(None) - deliver the cooked food

Remember that two agents must work together.
Only agent1 is able to slice foods on a cutboard.
agent2 should pick up foods and plates and place them on the counter for agent1.

When I ask you to do something, please give me a list of tasks in Python code that is needed to achieve the goal.
You must strictly satisfy the following requirements when you write code for me:
- You must put your code in a single Markdown code block starting with ```python and ending with ```.
- You must not use any hypothetical functions or variables that you think exist. Use only the functions that I listed above.
- Your code must be immediately executable via the exec() function.
- You must create a list named task_queue and store each function and its argument as a tuple.

Get ready!
"""

ocma_example = """```python
# the goal is to make a lettuce salad. Think about what tasks need to be accomplished step by step.
task_queue = []

# 1. agent2 picks up lettuce
task_queue.append((agent2.fetch, "lettuce"))

# 2. agent2 puts the lettuce onto counter0 for agent1 (agent2 already has lettuce in hand)
task_queue.append((agent2.put_onto, "counter0"))

# 3. agent1 picks up the lettuce from counter0
task_queue.append((agent1.fetch, "lettuce"))

# 4. agent1 puts the lettuce onto cutboard0 (agent1 already has lettuce in hand)
task_queue.append((agent1.put_onto, "cutboard0"))

# 5. agent1 slices the lettuce (lettuce is already on cutboard0). remember: only agent1 can slice foods
task_queue.append((agent1.slice_on, "cutboard0"))

# 6. agent2 picks up plate0
task_queue.append((agent2.fetch, "plate0"))

# 7. agent2 puts plate0 onto counter0 for agent1
task_queue.append((agent2.put_onto, "counter0"))

# 8. agent1 picks up the sliced lettuce
task_queue.append((agent1.fetch, "lettuce"))

# 9. agent1 puts the sliced lettuce onto plate0 (agent1 already has the sliced lettuce in hand)
task_queue.append((agent1.put_onto, "plate0"))

# 10. agent1 picks up the plate with the sliced lettuce
task_queue.append((agent1.fetch, "lettuce"))

# 11. agent1 delivers (agent1 already has the salad in hand)
task_queue.append((agent1.deliver, None))
```
"""