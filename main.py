from fastapi import FastAPI, Request
from typing import Dict, Any,List, Optional, Union
from langgraph.graph import StateGraph, MessagesState
import uvicorn
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel
from dotenv import load_dotenv
from neo4j import GraphDatabase
import json
from langchain_neo4j import GraphCypherQAChain
from langchain.chat_models import init_chat_model
from langchain_neo4j import Neo4jGraph

#------------------------------------------------------------------------------------
load_dotenv()
driver = GraphDatabase.driver("neo4j://127.0.0.1:7687", auth=("neo4j", "Rumbling@1990"))
graph = Neo4jGraph(
    url='neo4j://127.0.0.1:7687',
    username="neo4j", 
    password="Rumbling@1990",
)

def create_graph_with_parameters(nodes_data):
    nodes_data = [nodes_data]  # wrap in list
    path_to_node = {node["path"]: node for node in nodes_data}

    with driver.session() as session:
        # 1. Create HoudiniNode + Parameter nodes
        for node in nodes_data:
            session.run("""
                MERGE (n:HoudiniNode {path: $path})
                SET n.name = $name, n.type = $type
            """, {
                "path": node["path"],
                "name": node["name"],
                "type": node["type"]
            })

            # Create Parameter nodes and link to HoudiniNode
            for key, value in node.get("parameters", {}).items():
                session.run("""
                    MERGE (p:Parameter {key: $key})
                    SET p.value = $value
                    WITH p
                    MATCH (n:HoudiniNode {path: $node_path})
                    MERGE (n)-[:HAS_PARAMETER]->(p)
                """, {
                    "key": key,
                    "value": value,
                    "node_path": node["path"]
                })

        # 2. CONNECTED_TO relationships
        for node in nodes_data:
            for input_path in node.get("inputs", []):
                if input_path in path_to_node:
                    session.run("""
                        MATCH (from:HoudiniNode {path: $from})
                        MATCH (to:HoudiniNode {path: $to})
                        MERGE (from)-[:CONNECTED_TO]->(to)
                    """, {
                        "from": input_path,
                        "to": node["path"]
                    })

        # 3. CHILD_OF hierarchy relationships (optional)
        for node in nodes_data:
            parent_path = node.get("parent")
            if parent_path and parent_path in path_to_node:
                session.run("""
                    MATCH (child:HoudiniNode {path: $child})
                    MATCH (parent:HoudiniNode {path: $parent})
                    MERGE (child)-[:CHILD_OF]->(parent)
                """, {
                    "child": node["path"],
                    "parent": parent_path
                })
        print("updated sucesfully")
#------------------------------------------------------------------------------------

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
cypher_model = init_chat_model(
    "gpt-4o", 
    model_provider="openai",
    temperature=0.0
)

cypher_qa = GraphCypherQAChain.from_llm(
    graph=graph, 
    llm=model, 
    allow_dangerous_requests=True,
    verbose=True, 
)



def safe_json_decode(content):
    if isinstance(content, dict):
        return content  
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
        Set the scale to 1. Set rz to 20.Set ry to 15.
    """
    response = cypher_qa.invoke(input={"query": "Set the scale to 5. Set rz to 90. Set ry to 10."})
    print(response)
    
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
    create_graph_with_parameters(data)
    # Create initial LangGraph-compatible state
    invoke_data = State(
        messages=[
            HumanMessage(content="Process this Houdini data")
        ],
        data=data
    )
    result = graph.invoke(invoke_data)
    # create_graph_with_parameters(result['data'])
    return {
        "data": result['data']
    }


