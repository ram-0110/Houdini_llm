from fastapi import FastAPI, Request
from typing import Dict, Any,List, Optional, Union
from langgraph.graph import StateGraph, MessagesState
import uvicorn
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel
from dotenv import load_dotenv
import json

#------------------------------------------------------------------------------------
load_dotenv()

class State(MessagesState):
    data: Dict[str, Any]
# Define schema
class ParameterTemplate(BaseModel):
    name: str
    label: str
    type: str
    default: Optional[Union[List[float], List[int], float, int, bool]] = None

class HoudiniNode(BaseModel):
    name: str
    path: str
    type: str
    parent: str
    inputs: List[str]
    outputs: List[str]
    parameters: dict
    parmTemplates: List[ParameterTemplate]
    children: List[str]

parser = PydanticOutputParser(pydantic_object=HoudiniNode)

with open("prompt.txt", "r", encoding="utf-8") as file:
    prompt = file.read()


model = ChatOpenAI(model="gpt-4o-mini-2024-07-18", temperature=0)



def safe_json_decode(content):
    if isinstance(content, dict):
        return content  # already decoded ✅
    if isinstance(content, str):
        try:
            decoded_once = json.loads(content)
            if isinstance(decoded_once, str):
                # still a string? decode again
                return json.loads(decoded_once)
            return decoded_once
        except Exception as e:
            raise ValueError(f"Failed to decode JSON: {e}")
    raise TypeError(f"Unexpected content type: {type(content)}")


def process_houdini_node(state: State) -> State:
    houdini_json=state['data']
    human_prompt=f"""
        {parser.get_format_instructions()}

        Input:
        {houdini_json}

        Instructions:
        Set the scale to 1. Set ry to 0.Set ry to 0.
    """


    
    state["messages"]=[HumanMessage(human_prompt)]
    
    result=model.invoke([prompt]+ state["messages"])
    final_data = safe_json_decode(result.content)
    state["data"]=final_data
    return state



builder = StateGraph(State)
builder.add_node("process", process_houdini_node)
builder.set_entry_point("process")
graph = builder.compile()


#------------------------------------------------------------------------------------
app = FastAPI()

@app.post("/receive-houdini-data")
async def receive_data(request: Request):
    data = await request.json()

    # Create initial LangGraph-compatible state
    invoke_data = State(
        messages=[
            HumanMessage(content="Process this Houdini data")
        ],
        data=data
    )
    result = graph.invoke(invoke_data)

    
    return {
        "data": result['data']
    }
