import hou
import requests
import json


def safe_default(val):
    try:
        if isinstance(val, (tuple, list)):
            return [safe_default(v) for v in val]
        elif isinstance(val, (int, float, str, bool)) or val is None:
            return val
        else:
            return str(val)
    except:
        return str(val)

def export_node_structure(node):
    data = {
        "name": node.name(),
        "path": node.path(),
        "type": node.type().name(),
        "parent": node.parent().path() if node.parent() else None,
        "inputs": [input_node.path() if input_node else None for input_node in node.inputs()],
        "outputs": [output.path() for output in node.outputs()],
        "parameters": {},
        "parmTemplates": [],
        "children": [child.path() for child in node.children()]
    }

    for parm in node.parms():
        try:
            value = parm.eval()
            data["parameters"][parm.name()] = safe_default(value)
        except:
            pass

    ptg = node.parmTemplateGroup()
    for pt in ptg.parmTemplates():
        data["parmTemplates"].append({
            "name": pt.name(),
            "label": pt.label(),
            "type": pt.type().name(),
            "default": safe_default(pt.defaultValue())
        })

    return data


def apply_node_structure(data):
    node_path = data["path"]
    parent_path = data["parent"]
    node_name = data["name"]
    node_type = data["type"]

    # Get or create parent node
    parent = hou.node(parent_path)
    if not parent:
        raise ValueError(f"Parent node '{parent_path}' does not exist")

    # Get or create the node
    node = hou.node(node_path)
    if not node:
        node = parent.createNode(node_type, node_name)

    # Set parameters
    for parm_name, value in data.get("parameters", {}).items():
        parm = node.parm(parm_name)
        if parm is not None:
            try:
                parm.set(value)
            except Exception as e:
                print(f"Could not set parameter '{parm_name}': {e}")
        else:
            print(f"Parameter '{parm_name}' not found on node '{node_path}'")

    # Connect inputs
    inputs = data.get("inputs", [])
    for i, input_path in enumerate(inputs):
        if input_path:
            input_node = hou.node(input_path)
            if input_node:
                node.setInput(i, input_node)
            else:
                print(f"Input node '{input_path}' not found")

    # Optional: display flags, color, comment, etc.
    if data.get("displayFlag", False):
        node.setDisplayFlag(True)

    if "color" in data:
        color = hou.Color(data["color"])
        node.setColor(color)

    if "comment" in data:
        node.setComment(data["comment"])

    return node


node=hou.node('/obj/geo1/box1')
data=export_node_structure(node)
print(json.dumps(data, indent=2))
node_data = export_node_structure(hou.node("/obj/geo1/box1"))


response = requests.post(
    "http://localhost:8000/receive-houdini-data",
    json=node_data  
)

ed_data=response.json()
ed_data=ed_data['data']
print("----------------------------------------------------------------")



apply_node_structure(ed_data)



