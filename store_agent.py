from dotenv import load_dotenv
import os
import re
from langchain_openai import ChatOpenAI
from typing import TypedDict
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

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

def startNode(stream): #Exists to check if the graph loop should end and for the conditional edge
    return stream

def recommendationNode(stream):
    messages = stream["input"]
    last_message = messages[-1]

    response = model.invoke("I want you to extract only the item wanted from the following user input: " + last_message)
    response = response.content

    result = retrieve(collection, response)
    output = "We recommend -> " + result["documents"][0][0] + ", with url -> " + result["metadatas"][0][0]["url"] + " and image -> " + result["metadatas"][0][0]["image"]
    stream["input"].append(output)
    return stream

def sideQueryTool(stream):
    messages = stream["input"]
    last_message = messages[-1]
    response = model.invoke(messages)
    stream["input"].append(response.content)
    return stream

def endNode(stream):
    messages = stream["input"]
    last_message = messages[-1]
    if re.search(r'\bend\b|\bbye\b', last_message, re.IGNORECASE):
        stream["input"].append("Goodbye :D")
    return stream

def should_continue(state):
    messages = state["input"]
    last_message = messages[-1]

    if re.search(r'\brecommend\b', last_message, re.IGNORECASE):
        return "recommendation"
    elif re.search(r'\bend\b|\bbye\b', last_message, re.IGNORECASE):
        return "end"
    else:
        return "sideQuery"

workflow = StateGraph(State)    

workflow.add_node("start", startNode)
workflow.add_node("recommendation", recommendationNode)
workflow.add_node("sideQuery", sideQueryTool)
workflow.add_node("end", endNode)

workflow.add_conditional_edges("start", should_continue, {"recommendation":"recommendation" ,"end":"end", "sideQuery":"sideQuery"})
workflow.add_edge("recommendation", "end")
workflow.add_edge("sideQuery", "end")

workflow.set_entry_point("start")
workflow.set_finish_point("end")

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


