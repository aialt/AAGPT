import argparse
import time
import os
import yaml

from aagpt import AgentGPTMEM, AgentPCMEM
from env import Env
import util


os.system('cls' if os.name == 'nt' else 'clear')

def setup_world():
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--world_root', type=str, default='setup/game.yaml')
    args = parser.parse_args()
    
    # Load world setup from YAML file
    with open(args.world_root, 'r') as f:
        ws = yaml.load(f, Loader=yaml.FullLoader)
    
    # Perform common setup operations
    util.common(ws)
    
    return ws


def main_loop(agent, env):
    # Initialize time step counter
    time_step = 0
    
    # Main loop
    while True:
        time_step += 1
        
        # If agent has tasks to perform
        if agent.task_list:

            print("=" * os.get_terminal_size().columns)
            goal_des = " GOAL: " + agent.goal + " "
            print("\033[95m\033[1m" + "=" * ((os.get_terminal_size().columns - len(goal_des)) // 2) + goal_des + "=" * ((os.get_terminal_size().columns - len(goal_des)) // 2) + "\033[0m\033[0m")
            print("=" * os.get_terminal_size().columns)

            # Display the current tasks
            print("\033[94m\033[1m" + "\nTASK LIST:\n" + "\033[0m\033[0m")
            for t in agent.task_list:
                print("\033[94m" + str(t["task_id"]) + ": " + t["task_name"] + "\033[0m")

            # Perform the next task
            task = agent.act()
            print("\033[92m\033[1m" + "\nCURRENT TASK:\n" + "\033[0m\033[0m")
            print("\033[92m" + task["task_name"] + "\033[0m")

            # Execute the task in the environment
            result = env.exec(agent, task)
            print("\033[93m\033[1m" + "\nRESULT:\n" + "\033[0m\033[0m")
            print("\033[93m" + result + "\033[0m")

            # Update the agent with the task result
            agent.receive(result)

        print("\n" + "\033[91m" + "LIFE: " + str(time_step) + "/" + str(agent.life)+ "\033[0m")
        # Sleep for 1 second before the next iteration
        time.sleep(1)

        # End the loop if the agent's life is over
        if time_step > agent.life:
            print("\nGood Game:)")
            break


if __name__ == "__main__":
    # Set up the world
    ws = setup_world()
    
    # Create the agent based on the world setup
    if ws["agent"]["agent_type"] == "agent_gptmem":
        agent = AgentGPTMEM(ws)
    else:
        agent = AgentPCMEM(ws)
    
    # Create the environment
    env = Env(ws)
    
    # Start the main loop
    main_loop(agent, env)
    