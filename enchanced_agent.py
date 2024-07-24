from dotenv import load_dotenv
import os
import re
from langchain_openai import ChatOpenAI
from typing import TypedDict
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain.schema import AIMessage
from langgraph.graph import StateGraph, START, END

from database import createDB, addItemsDB, retrieve, dropDB

load_dotenv()

os.environ['OPENAI_API_KEY'] = os.environ.get("OPENAI_API_KEY")

model = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-0125") # model gpt

#------------Database

collection = createDB()
addItemsDB(collection)

#----------------------

class State(TypedDict):
    input: str

class MyTool(BaseTool):
    name = "my_tool"
    description = "Checks if there is a need for recommendation of an item"

    def _run(self, input: str) -> str:
        """Checks if there is a need for recommendation of an item"""
        prompt = f"The following will be a user input. I want you to check if the user wants a recommendation for an item and the query is adequate. If that is so, return only the item needed. Else, return 'END'. Input: {input}"
        response = model.invoke([HumanMessage(content=prompt)])
        return response.content

my_tool =  MyTool()
model.bind_tools([my_tool])

def agent_node(state):
    messages = state["input"]
    last_message = messages[-1]

    # Call the tool to check the user input
    tool_result = my_tool.invoke({"input": [last_message]})

    if tool_result == "END":
        response = model.invoke(last_message)
        state["input"].append(response.content)
        state["next_node"] = END
        return state
    else:
        state["input"].append(tool_result)
        state["next_node"] = "recommendation"
        return state

def recommendationNode(stream):
    messages = stream["input"]
    last_message = messages[-1]
    result = retrieve(collection, last_message)
    output = "We recommend -> " + result["documents"][0][0] + ", with url -> " + result["metadatas"][0][0]["url"] + " and image -> " + result["metadatas"][0][0]["image"]
    stream["input"].append(output)
    return stream
    
workflow = StateGraph(State)    

workflow.add_node("main", agent_node)
workflow.add_node("recommend", recommendationNode)

workflow.add_edge("main", END)
workflow.add_conditional_edges(
    "main",
    lambda state: state["next_node"],
    {"recommendation": "recommend", END: END}
)

workflow.set_entry_point("main")

memory = MemorySaver()

thread = {"configurable": {"thread_id": "1"}}

app = workflow.compile(checkpointer=memory)

userQuery = {"input" : [""]}
tempQuery = ""

while not re.search(r'\bend\b', tempQuery, re.IGNORECASE):
    tempQuery = input("---")
    output = ""
    userQuery["input"].append(tempQuery.lower())
    for event in app.stream(userQuery, thread, stream_mode="values"):
        # print(event)
        output = event
    print(output["input"][-1])