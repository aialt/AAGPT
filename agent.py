from collections import deque
from typing import Dict, List
from util import memory_as_pinecone, get_ada_embedding, openai_call


class AgentGPTMEM:
    def __init__(self, config):
        self.agent_config = config["agent"]
        self.task_list = deque([])
        self.life = self.agent_config["agent_life"]
        self.memory = self.build_memory()
        first_task = {"task_id": 1, "task_name": self.agent_config["init_task"]}
        self.add_task(first_task)
        self.task_id_counter = 1
        self.task_turnon = None
        self.goal = self.agent_config["goal"]

    def build_memory(self):
        # Initialize memory as an empty list
        history = []
        return history

    def act(self):
        # Get the next task from the task list
        self.task_turnon = self.task_list.popleft()
        return self.task_turnon

    def add_task(self, task: Dict):
        # Add a task to the task list
        self.task_list.append(task)

    def receive(self, result):
        enriched_result = {
            "data": result
        }  # This is where you should enrich the result if needed
        task = self.task_turnon

        # Add the task and its result to the memory
        self.memory.append({"task": task["task_name"], "result": result})

        # Create new tasks based on the result
        new_tasks = self.task_creation(
            self.goal,
            enriched_result,
            task["task_name"],
            [t["task_name"] for t in self.task_list],
        )

        # Add the new tasks to the task list
        for new_task in new_tasks:
            self.task_id_counter += 1
            new_task.update({"task_id": self.task_id_counter})
            self.add_task(new_task)
        self.this_task_id = int(task["task_id"])

        # Prioritize the tasks in the task list
        self.prioritization(self.this_task_id)

    def prioritization(self, this_task_id: int):
        task_names = [t["task_name"] for t in self.task_list]
        next_task_id = int(this_task_id) + 1
        prompt = f"""
        You are a task prioritization AI tasked with cleaning the formatting of and reprioritizing the following tasks: {task_names}.
        Consider the ultimate objective of your team:{self.goal}.
        Do not remove any tasks. Return the result as a numbered list, like:
        #. First task
        #. Second task
        Start the task list with number {next_task_id}."""
        response = openai_call(prompt)
        new_tasks = response.split("\n") if "\n" in response else [response]
        self.task_list = deque()
        for task_string in new_tasks:
            task_parts = task_string.strip().split(".", 1)
            if len(task_parts) == 2:
                task_id = task_parts[0].strip()
                task_name = task_parts[1].strip()
                self.task_list.append({"task_id": task_id, "task_name": task_name})

    def task_creation(
        self, objective: str, result: Dict, task_description: str, task_list: List[str]
    ):
        prompt = f"""
        You are a task creation AI that uses the result of an execution agent to create new tasks with the following objective: {objective},
        The last completed task has the result: {result}.
        This result was based on this task description: {task_description}. These are incomplete tasks: {', '.join(task_list)}.
        Based on the result, create new tasks to be completed by the AI system that do not overlap with incomplete tasks.
        Return the tasks as an array."""
        response = openai_call(prompt)
        new_tasks = response.split("\n") if "\n" in response else [response]
        return [{"task_name": task_name} for task_name in new_tasks]
    
    def context_search(self, n: int, lookback = 10):
        completed_tasks = [ item["result"] + "\n" for item in self.memory[-lookback:]]
        prompt = f"""
        You are a task creation AI that uses the result of an execution agent to search finished tasks with the following objective: {self.goal},
        The rencent completed tasks are: {completed_tasks}.
        Based on the completed tasks, find tasks that are releveant to the objective.
        Return the tasks as an array."""
        response = openai_call(prompt)
        return response
    

class AgentPCMEM:
    def __init__(self, config):
        self.agent_config = config["agent"]
        self.pinecone_index = self.agent_config["agent_pinecone_index"] 
        self.task_list = deque([])
        self.memory = self.build_memory()
        self.life = self.agent_config["agent_life"]
        first_task = {"task_id": 1, "task_name": self.agent_config["init_task"]}
        self.add_task(first_task)
        self.task_id_counter = 1
        self.task_turnon = None
        self.goal = self.agent_config["goal"]

    def build_memory(self):
        """Create Pinecone index and return it as memory."""
        index = memory_as_pinecone(self.pinecone_index)
        return index

    def act(self):
        self.task_turnon = self.task_list.popleft()
        return self.task_turnon

    def add_task(self, task: Dict):
        self.task_list.append(task)

    def receive(self, result):
        
        enriched_result = {"data": result}
        task = self.task_turnon
        result_id = f"result_{task['task_id']}"
        vector = get_ada_embedding(enriched_result["data"]) 
        self.memory.upsert(
            [(result_id, vector, {"task": task["task_name"], "result": result})],
	    namespace=self.goal
        )
    
        new_tasks = self.task_creation(
            self.goal,
            enriched_result,
            task["task_name"],
            [t["task_name"] for t in self.task_list],
        )

        for new_task in new_tasks:
            self.task_id_counter += 1
            new_task.update({"task_id": self.task_id_counter})
            self.add_task(new_task)
        self.this_task_id = int(task["task_id"])
        
        self.prioritization(self.this_task_id)
    
    def prioritization(self, this_task_id: int):
        task_names = [t["task_name"] for t in self.task_list]
        next_task_id = int(this_task_id) + 1
        prompt = f"""
        You are a task prioritization AI tasked with cleaning the formatting of and reprioritizing the following tasks: {task_names}.
        Consider the ultimate objective of your team:{self.goal}.
        Do not remove any tasks. Return the result as a numbered list, like:
        #. First task
        #. Second task
        Start the task list with number {next_task_id}."""
        response = openai_call(prompt)
        new_tasks = response.split("\n") if "\n" in response else [response]
        self.task_list = deque()
        for task_string in new_tasks:
            task_parts = task_string.strip().split(".", 1)
            if len(task_parts) == 2:
                task_id = task_parts[0].strip()
                task_name = task_parts[1].strip()
                self.task_list.append({"task_id": task_id, "task_name": task_name})

    def task_creation(
        self, objective: str, result: Dict, task_description: str, task_list: List[str]
    ):
        prompt = f"""
        You are a task creation AI that uses the result of an execution agent to create new tasks with the following objective: {objective},
        The last completed task has the result: {result}.
        This result was based on this task description: {task_description}. These are incomplete tasks: {', '.join(task_list)}.
        Based on the result, create new tasks to be completed by the AI system that do not overlap with incomplete tasks.
        Return the tasks as an array."""
        response = openai_call(prompt)
        new_tasks = response.split("\n") if "\n" in response else [response]
        return [{"task_name": task_name} for task_name in new_tasks]
    

    def context_search(self, n: int):
        query_embedding = get_ada_embedding(self.goal)
        results = self.memory.query(query_embedding, top_k=n, include_metadata=True, namespace=self.goal)
        sorted_results = sorted(results.matches, key=lambda x: x.score, reverse=True)
        return [(str(item.metadata["task"])) for item in sorted_results]