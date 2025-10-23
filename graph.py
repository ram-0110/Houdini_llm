# %%
from typing import List,TypedDict,Optional,Any,Union,Set, Tuple
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_core.messages import HumanMessage,SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate,PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.schema.runnable import Runnable,RunnableLambda
from pydantic import BaseModel,Field
from dotenv import load_dotenv
from langchain.tools import tool
from typing import Dict
import os
from IPython.display import Image, display
import json
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# %%
final_data = []
nodes_list=[]
messages=[]

# %%
model1=ChatOpenAI(model='gpt-4.1-2025-04-14',temperature=0)
model2 = ChatGoogleGenerativeAI(model="gemini-2.5-pro",temperature=0)


# %%
with open('houdini_node_docs_all.json', 'r') as f:
    data = json.load(f)

# %%
allowed_type=[]
for item in data:
    allowed_type.append(item['type'])

# %%
def append_input(data, target_name, input_data):
    for item in data:
        if item['name'] == target_name:
            item['inputs'].append(input_data)
            break

def get_path_by_name(data, target_name):
    for item in data:
        if item['name'] == target_name:
            return item['path']
    return None  


# %%
def graph_structure_rem(data):
    graph_structure=data
    return graph_structure

def accepted_parms(check_data):
    unique_node_names = list({i['type'] for i in check_data})
    
    accepted_parameters = []

    for item in data:
        if item['type'] in unique_node_names:
            temp={}
            temp[item['type']] = item['parameters']
            accepted_parameters.append(temp)
    return accepted_parameters


# %%
@tool
def create_node(node_name: str, node_type: str, location: str) -> str:
    """
    Create a Houdini node with the specified name, type, and location.

    This tool constructs a new node representation and adds it to the shared node data structure.
    It does not physically create the node in Houdini but prepares a structured dictionary for later use.

    Args:
    - node_name (str): The name of the node to be created.
    - node_type (str): The type of the node.
    - location (str): The Houdini path where the node should be placed.

    Returns:
    - str: A success message confirming the node creation and its full path.
    """
    temp = {}
    path = f'{location}/{node_name}'

    temp['name'] = node_name
    temp['type'] = node_type
    temp['path'] = path
    temp['inputs'] = []
    temp['parameters'] = {}

    final_data.append(temp)

    return f"Node '{node_name}' of type '{node_type}' created at '{path}'."


@tool
def wiring_nodes(source_node: str, input_index: int, target_node: str) -> str:
    """
    Connects two Houdini nodes by wiring the output of a source node 
    to a specified input port of a target node.

    This tool retrieves the path of the source node and appends it 
    as an input connection to the target node at the given input index.

    Args:
        source_node (str): The name or identifier of the node providing the output.
        input_index (int): The input port index on the target node to connect to.
                           If unspecified, 0 is assumed by the agent logic.
        target_node (str): The name or identifier of the node receiving the input.

    Returns:
        str: A confirmation message indicating the wiring action was successful.
    """
    temp = {}
    path = get_path_by_name(final_data, source_node)

    temp['index'] = input_index
    temp['path'] = path

    append_input(final_data, target_node, temp)
    return f"Wired {source_node} to {target_node} at input index {input_index}."

@tool
def parameter_update(node_name: str, parameter_name: str, value) -> str:
    """
    Updates a specific parameter of a Houdini node with a new value.

    This tool locates the node by its name and sets the given parameter 
    to the specified value within the node's parameter dictionary.

    Args:
        node_name (str): The name or identifier of the Houdini node to modify.
        parameter_name (str): The name of the parameter to be updated.
        value: The new value to assign to the parameter. Can be of any valid type.

    Returns:
        str: A confirmation message indicating the parameter update was successful.
    """
    for data in final_data:
        if node_name == data['name']:
            data['parameters'][parameter_name] = value
            return f"Updated parameter '{parameter_name}' of node '{node_name}' to {value}."
    return f"Node '{node_name}' not found."



# %%
node_prompt=f"""
You are an expert in using SideFX Houdini.

Your task is to **build a complete procedural node network** using SideFX Houdini.
- **Creating nodes**
- **Wiring them together**

You must only use the following node types:
{allowed_type}

---

## NODE MODELING WORKFLOW

1. **Analyze the Object**  
   Decompose the target object into simple, manageable components or primitive forms.

2. **Determine Modeling Strategy**  
   For each component:
   - Choose the most effective modeling technique.
   - Justify your choices with brief reasoning when applicable.

3. **Create Nodes**  
   For each part:
   - Define the **Node Type**, **Node Name**, and **Location** (under `/obj/geo1`).
---

## NODE WIRING WORKFLOW

4. **Analyze the Nodes**  
   Understand the purpose and input/output of each node.

5. **Determine Connection Strategy**  
   For each node:
   - Identify the correct **source node** providing the required input.
   - Specify the **input port index** (default is 0).

6. **Wire the Nodes**  
   Connect the nodes using correct SOP data flow. Ensure no circular dependencies or invalid setups.

7. **Repeat**  
   Continue modeling and wiring until the complete object is procedurally modeled.

---

## OUTPUT FORMAT

### For Each Node:
- **Node Name**: A short, descriptive identifier.
- **Node Type**: One of the allowed SOP types.
- **Location**: Houdini path where the node will be created.
- **Purpose** *(optional)*: Why this node is needed.

### For Each Connection:
- **Source Node**: Name of the node providing output.
- **Input Index**: Input port on the target node (default is 0).
- **Target Node**: Name of the receiving node.
- **Purpose** *(optional)*: Why this connection is valid or necessary.


## Guidelines
- Begin all node creation under the `/obj/geo1` path.
- Avoid node types requiring interactive drawing (e.g., `curve`, `draw_curve`).
- Maintain procedural clarity, modular structure, and logical flow.
-Should end with a null node
- Think like a Houdini TD: prioritize **technical accuracy**, **efficiency**, and **clear reasoning** behind each decision.

-Return a final report summarizing your procedural work
"""

# %%
wireing_prompt=""" 
You are a **Technical Director (TD)** specializing in **Geometry (SOP) networks procedural modeling** in SideFX Houdini.

Your task is to **connect a sequence of nodes** to form a valid procedural network, using a clear, step-by-step and logical breakdown.

---

### Wiring Workflow

1. **Analyze the Nodes**  
   Review the purpose of each node and understand its data requirements and outputs.

2. **Determine Connection Strategy**  
   For each node:
   - Identify the correct **source node** that provides the expected input.
   - Select the appropriate **input port index** on the target node (default is 0 if not specified).
   - Justify non-obvious connections briefly.

3. **Wire the Nodes**  
   Create the connection between the source_node and target_node using the correct port index.

4. **Repeat**  
   Continue this process until all necessary connections are established and the network is valid.

---

### Guidelines

- Ensure that connections follow Houdini’s SOP data flow logic.
- Avoid circular dependencies or invalid combinations of node types.
- Maintain a logical and readable wiring structure, supporting modularity and clarity.

---

### Output Format

For each connection, specify:

- **Source Node**: Name or identifier of the node providing output.
- **Input Index**: Input port index on the receiving node (default is 0 if omitted).
- **Target Node**: Name or identifier of the node receiving input.
- **Purpose** *(optional)*: Brief explanation of why this connection is valid or necessary.

Think like a Houdini TD: balance technical correctness, procedural clarity, and logical structure. Avoid ambiguity—be precise, deliberate, and explicit in your wiring decisions.


"""

# %%
parameter_update_prompt = """
You are an expert in using SideFX Houdini.

Your task is to **analyze an existing SOP node network** and **adjust the parameters** of specific nodes to refine the geometry output.

You will be provided with:
-A object to model
- A list of nodes in the network and how they are connected
{graph_structure}
- The allowed parameters for each node type:
{allowed_parameters}

---

## PARAMETER UPDATING WORKFLOW

1. **Analyze the Node Network**  
 - Review all nodes in the network and how they are connected.
 - Understand each node's function and contribution to the overall geometry.

2. **Determine Which Parameters to Update**  
 - Decide which parameter values, if modified, would bring the geometry closer to the desired result.

3. **Update Parameters**  
 For each parameter change:
 - Identify the **node name** to update.
 - Specify the **parameter name** to modify.
 - Provide a valid **value** appropriate to the parameter type.

4. **Repeat**  
 Continue updating parameters iteratively until the geometry aligns with the modeling objective.

---

## OUTPUT FORMAT

For each update, return:
- `node_name` (str): The name of the Houdini node to modify.
- `parameter_name` (str): The parameter to update.
- `value`: The new value to assign (should match the expected type for that parameter).


"""

# %%
def run_agent(model_prompt:str):
    messages=[]

    question=HumanMessage(model_prompt)
    messages.append(question)

    node_agent=create_react_agent(model=model1,tools=[create_node,wiring_nodes],prompt=node_prompt,name="Nodes_agent",)
    result=node_agent.invoke({'messages':messages})

    messages.append(result['messages'][-1])
    # messages.append(HumanMessage("now wire those nodes"))

    # wiring_agent=create_react_agent(model=model1,tools=[wiring_nodes],prompt=wireing_prompt,name="Wireing_agent",)
    # result1=wiring_agent.invoke({'messages': messages})

    # messages.append(result1['messages'][-1])
    # print(result1['messages'])


    parameter_agent=create_react_agent(model=model1,tools=[parameter_update],prompt=parameter_update_prompt.format(allowed_parameters=accepted_parms(final_data),graph_structure=graph_structure_rem(final_data)),name="Parameter_agent",)
    result2=parameter_agent.invoke({'messages':messages})

    return_final_data = final_data.copy()  
    final_data.clear()  

    return return_final_data

