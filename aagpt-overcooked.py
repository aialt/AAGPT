import argparse
import cv2
import yaml
from overcooked.agent import GPTAgent, ChatBot
from overcooked.env import OvercookedEnvGPT
from overcooked.utils import get_task_queue, colors, fix_seed


"""
ChatGPT for Overcooking
"""
def parse_arguments():
    parser = argparse.ArgumentParser("Overcooked 2 argument parser")
    # Environment
    parser.add_argument('--world_root', type=str, default='setup/gameovercooked.yaml')
    parser.add_argument("--max-num-timesteps", type=int, default=100, help="Max number of timesteps to run")
    parser.add_argument("--max-num-subtasks", type=int, default=14, help="Max number of subtasks for recipe")
    parser.add_argument("--seed", type=int, default=1, help="Fix pseudorandom seed")
    parser.add_argument("--with-image-obs", action="store_true", default=True, help="Return observations as images (instead of objects)")
    # Visualizations
    parser.add_argument("--record", action="store_true", default=False, help="Save observation at each time step as an image in misc/game/record")
    parser.add_argument("--render", action="store_true", help="render the images")
    # GPT
    parser.add_argument("--gpt", action="store_true", default=True)
    return parser.parse_args()


def main_loop(args):
    """The main loop for running experiments."""
    print("Initializing environment and agents.")
    
    # Load world setup from YAML file
    with open(args.world_root, 'r') as f:
        ws = yaml.load(f, Loader=yaml.FullLoader)
    
    num_agents = ws["common"]["agents"]["n"]
    level =  ws["common"]["level"]
    env = OvercookedEnvGPT(num_agents, level, arglist=args)
    obs = env.reset()
    
    # initialize the agent
    agent1 = GPTAgent(1, level, args)
    agent2 = GPTAgent(2, level, args)

    chatbot = ChatBot(num_agents, ws, args)

    task_queue = get_task_queue(ws, chatbot, agent1, agent2) 

    # start to do the queue 
    task_id, cur_agent_id, global_steps, max_steps = 0, 0, 1, 200
    # initialise the agent's state
    action_dict = {'agent-1': (0, 0), 'agent-2': (0, 0)}
    _, _, _, info = env.step(action_dict=action_dict)
    while True:
        f = task_queue[task_id][0]
        arg = task_queue[task_id][1]
        if str(agent1) in str(f):
            cur_agent_id = 1
            print("agent1 is in the task")
            agent1.reset_state()
            # update state
            agent1_states = info["agents_states"]["agent-1"]
            agent1.set_state(location=agent1_states["loc"], action_str=agent1_states["action_str"], action_loc=agent1_states["action_loc"])
        elif str(agent2) in str(f):
            cur_agent_id = 2
            print("agent2 is in the task")
            agent2.reset_state()
            # update state
            agent2_states = info["agents_states"]["agent-2"]
            agent2.set_state(location=agent2_states["loc"], action_str=agent2_states["action_str"], action_loc=agent2_states["action_loc"])
        # execute the subtask...
        subtask_finish, action = f(arg)
        if cur_agent_id == 1:
            action_dict = {'agent-1': action, 'agent-2': (0, 0)}
        elif cur_agent_id == 2:
            action_dict = {'agent-1': (0, 0), 'agent-2': action}
        # execute the action and  
        _, _, _, info = env.step(action_dict=action_dict)
        global_steps += 1
        if global_steps > max_steps:
            print("Max Timestep Has Reached!")
            break
        if args.render:
            cv2.imshow('Overcooked', info['image_obs'][:,:,::-1])
            cv2.waitKey(30)
        if subtask_finish:
            print(colors.GREEN + f"task complete: {str(f)}({str(arg)})" + colors.ENDC)
            task_id += 1
            if task_id == len(task_queue):
                print(colors.GREEN + f"ALL TASKS COMPLETE: score={global_steps} (lower the better)" + colors.ENDC)
                break


if __name__ == '__main__':
    args = parse_arguments()
    fix_seed(seed=args.seed)
    main_loop(args)
