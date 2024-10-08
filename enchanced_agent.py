from dotenv import load_dotenv
import os
import re
from langchain_openai import ChatOpenAI
from typing import TypedDict
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, END
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
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
    next_node: str
    recommended: list[str]

def callPromptChain(recommended, messages):
    prePrompt = ""
    last_message = messages[-1]
    with open('./agent_data.txt', 'r') as file:
        prePrompt = file.read()
    items = ", ".join(recommended)
    prompt = PromptTemplate(
        input_variables=["prePrompt","items", "last_message", "messages"],
        template= "{prePrompt} The following are items that you have recommended to this client: {items}. Here is your memmory component: {messages} I want you to use them as a refference when desciding if you can recommend an item. Please respond to the user's query: {last_message} in a professional manner without redundant greetings or farewells.")
    chain = prompt | model | StrOutputParser()
    chain_input = {
        "prePrompt": prePrompt,
        "items": items,
        "last_message": last_message,
        "messages": messages
    }
    result = chain.invoke(chain_input)
    return result

# Define_prompt function. Gets callled by out 

class MyTool(BaseTool):
    name = "my_tool"
    description = "Checks if there is a need for recommendation of an item"

    def _run(self, input: str) -> str:
        """Checks if there is a need for recommendation of an item"""
        prompt = f"The following will be a user input. I want you to check if the user wants a recommendation for an item and the query is adequate. If that is so, return only the query. Else, return 'END'. Input: {input}"
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
        response = callPromptChain(userQuery["recommended"], messages)
        state["input"].append(response)
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
    stream["recommended"].append(output)
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

userQuery = {"input" : [""], "next_node" : "", "recommended" : []}
tempQuery = ""

def bongoAgent(query):
        output = ""
        print(query)
        userQuery["input"].append(query.lower())
        for event in app.stream(userQuery, thread, stream_mode="values"): 
            output = event
            # print(output)
        return(output["input"][-1])

# while not re.search(r'\bbye\b', tempQuery, re.IGNORECASE):
#     tempQuery = input("---")
#     output = ""
#     userQuery["input"].append(tempQuery.lower())
#     #Make a server call for the query
#     for event in app.stream(userQuery, thread, stream_mode="values"): 
#         # print(event)
#         output = event
#     #Make a server call for the output
#     print(output["input"][-1])
