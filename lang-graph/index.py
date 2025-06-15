from dotenv import load_dotenv 

load_dotenv() 

from pydantic import BaseModel
from langchain_core.messages import AnyMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()

def get_weather(location: str) -> str:
    """
    A mock function to simulate getting weather information.
    Args:
        location (str): The location for which to get the weather.
    Returns:
        str: A string indicating the weather in the specified location.
    """
    return f"The weather in {location} is kak."

class WeatherResponse(BaseModel):
    conditions: str
    city: str
    query_number: int

def prompt(state: AgentState, config: RunnableConfig) -> list[AnyMessage]:  
    user_name = config["configurable"].get("user_name")
    system_msg = f"You are a helpful assistant. Address the user as {user_name}."
    return [{"role": "system", "content": system_msg}] + state["messages"]

agent = create_react_agent(
    model="openai:gpt-4.1",
    tools=[get_weather],
    prompt=prompt,
    checkpointer=checkpointer,
    response_format=WeatherResponse
)

config = {"configurable": {"user_name": "Jaak", "thread_id": "test-1"}}
responses = []
responses.append(
    agent.invoke(
        {"messages": [{"role": "user", "content": "what is the weather in sf"}]},
        config=config
    )
)

response = responses.pop()
print("Response 1")
print(response["messages"][-1].content)
print(response["structured_response"])
print()

responses.append(
    agent.invoke(
        {"messages": [{"role": "user", "content": "what is the weather in pta"}]},
        config=config
    )
)

response = responses.pop()
print("Response 2")
print(response["messages"][-1].content)
print(response["structured_response"])
print()