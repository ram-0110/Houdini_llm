from fastapi import FastAPI, Request
import uvicorn
import sys
import os
from Final_working import run_agent
from pydantic import BaseModel

app = FastAPI()

class InputData(BaseModel):
    nodes: str


@app.post("/receive-houdini-data")
async def receive_data(data:InputData):
    print("Received string:", data.nodes)
    return_data=run_agent(data.nodes)
    print(return_data)
    return {"data": return_data}


if __name__=='__main__':
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
