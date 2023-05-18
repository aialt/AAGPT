from utils import openai_call


class Env:
    def __init__(self, config):
        self.env_config = config["env"]

    def exec(self, agent, task):
        """Execute the given task using the agent and return the result."""
        # Get the context of the top 5 related tasks from the agent's memory
        context = agent.context_search(5)

        # Extract the task name
        task = task["task_name"]

        # Prepare the prompt for the AI
        prompt = f"""
            You are an AI who performs one task based on the following objective: {agent.goal}\n.
            Take into account these previously completed tasks: {context}\n.
            Your task: {task}\nResponse:"""

        # Call the OpenAI API to get the result
        return openai_call(prompt, temperature=0.7, max_tokens=2000)