import hou
import json
import pprint

#-------------------------------------------------------------------------------

def extract_nodes():
    obj=hou.node('/obj')
    children=obj.children()
    data=[]
    for node in children:
        for child_node in node.children():
            temp={}
            temp['name']=child_node.name()
            temp['type']=child_node.type().name()
            temp['path']=child_node.path()
            temp['inputs']=[]
            inputs = child_node.inputs()
            
            for idx, input_node in enumerate(inputs):
                temp1={}
                if input_node:
                    temp1['index']=idx
                    temp1['path']=input_node.path()
                    temp['inputs'].append(temp1)
                else:
                    print(f"Input {idx}: None")
                    
            parm=child_node.parms()
            temp2={}
            for p in parm:
                temp2[p.name()]=p.eval()
            temp['parameters']=temp2
            data.append(temp)
    return data

#-------------------------------------------------------------------------------
def create_node_parm(data):
     geo_node = hou.node("/obj/geo1")
     for item in data:
        node_cr=geo_node.createNode(item['type'],item['name'])
        for param_name, param_value in item["parameters"].items():
            node_cr.parm(param_name).set(param_value)


def create_graph(data):
    geo_node = hou.node("/obj/geo1")
    create_node_parm(data)
    for item in data:
        node_cr=hou.node(item['path'])
        for inp in item['inputs']:
            sub_node=hou.node(inp['path'])
            if sub_node is None:
                print(f"ERROR: Could not find node at path: {inp['path']}")
            else:
                node_cr.setInput(inp['index'],sub_node)

#-------------------------------------------------------------------------------


# data=extract_nodes()
# print(json.dumps(data, indent=2))


#-------------------------------------------------------------------------------




import requests


prompt = "Tea cup"

response = requests.post(
    "http://localhost:8000/receive-houdini-data",
    json={"nodes": prompt}
)


edited_nodes_data = response.json().get("data", [])
create_graph(edited_nodes_data)
