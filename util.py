import subprocess
import time
import openai
import pinecone


OPENAI_API_MODEL = ""

def common(config):
    # Set up API keys and models from the configuration
    OPENAI_API_KEY = config['common']['openai_api_key']
    assert OPENAI_API_KEY, "OPENAI_API_KEY environment variable is missing from .env"

    global OPENAI_API_MODEL
    OPENAI_API_MODEL = config['common']['openai_model']
    assert OPENAI_API_MODEL, "OPENAI_API_MODEL environment variable is missing from .env"

    # Print a message if using GPT-4
    if "gpt-4" in OPENAI_API_MODEL.lower():
        print("\033[92m\033[1m\n>>USING GPT-4.\033[0m\033[0m")

    # Get the goal and initial task from the configuration
    OBJECTIVE = config['agent']['goal']
    INITIAL_TASK = config['agent']['init_task']

    assert OBJECTIVE, "OBJECTIVE environment variable is missing from .env"
    assert INITIAL_TASK, "INITIAL_TASK environment variable is missing from .env"

    # Print the agent's goal and initial task
    print("\033[92m\033[1m\n>>Agent's Goal\n\033[0m\033[0m")
    print(f"{OBJECTIVE}")
    print("\033[92m\033[1m\nInitial task:\033[0m\033[0m {INITIAL_TASK}")

    # Configure OpenAI and Pinecone
    openai.api_key = OPENAI_API_KEY

    if config["agent"]["agent_type"] == "agent_pineconemem":
        PINECONE_API_KEY = config['agent']['agent_pinecone_api_key'][0]
        assert PINECONE_API_KEY, "PINECONE_API_KEY environment variable is missing from .env"

        PINECONE_ENVIRONMENT = config['agent']['agent_pinecone_api_key'][1]
        assert PINECONE_ENVIRONMENT, "PINECONE_ENVIRONMENT environment variable is missing from .env"

        pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
  
def openai_call(
    prompt: str,
    temperature: float = 0.5,
    max_tokens: int = 100,
):
    model = OPENAI_API_MODEL
    while True:
        try:
            if model.startswith("llama"):
                # Spawn a subprocess to run llama.cpp
                cmd = ["llama/main", "-p", prompt]
                result = subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True)
                return result.stdout.strip()
            elif not model.startswith("gpt-"):
                # Use completion API
                response = openai.Completion.create(
                    engine=model,
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=1,
                    frequency_penalty=0,
                    presence_penalty=0,
                )
                return response.choices[0].text.strip()
            else:
                # Use chat completion API
                messages = [{"role": "system", "content": prompt}]
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    n=1,
                    stop=None,
                )
                return response.choices[0].message.content.strip()
        except openai.error.RateLimitError:
            print(
                "The OpenAI API rate limit has been exceeded. Waiting 10 seconds and trying again."
            )
            time.sleep(10)  # Wait 10 seconds and try again
        else:
            break

def get_ada_embedding(text):
    """Get the ada embedding of the given text."""
    text = text.replace("\n", " ")
    return openai.Embedding.create(input=[text], model="text-embedding-ada-002")[
        "data"
    ][0]["embedding"]

def memory_as_pinecone(table_name):
    """Create a Pinecone index with the given table_name."""
    dimension = 1536
    metric = "cosine"
    pod_type = "p1"
    if table_name not in pinecone.list_indexes():
        pinecone.create_index(
                table_name, dimension=dimension, metric=metric, pod_type=pod_type
        )
    index = pinecone.Index(table_name)
    return index