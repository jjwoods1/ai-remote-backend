from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from redis import Redis
import os
import uuid
import time
import ast

app = FastAPI()

# Connect to Redis (env var or default localhost)
REDIS_URL = os.getenv("REDISHOST", "redis://localhost:6379")
r = Redis.from_url(REDIS_URL, decode_responses=True)

# Models
class CommandRequest(BaseModel):
    agent_id: str
    command: str

class RegisterRequest(BaseModel):
    agent_id: str

class ResultRequest(BaseModel):
    task_id: str
    output: str

@app.get("/")
def root():
    return {"message": "AI Remote Backend is running"}

@app.post("/api/agent/register")
def register_agent(data: RegisterRequest):
    agent_id = data.agent_id
    if not agent_id:
        raise HTTPException(status_code=400, detail="Missing agent_id")
    try:
        r.sadd("agents", agent_id)
        return {"status": "registered", "agent_id": agent_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis error: {str(e)}")

@app.get("/api/agents/active")
def get_active_agents():
    try:
        agents = r.smembers("agents")
        return {"agents": list(agents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis error: {str(e)}")

@app.post("/api/command/send")
def send_command(req: CommandRequest):
    if not r.sismember("agents", req.agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")

    task_id = str(uuid.uuid4())
    payload = {
        "task_id": task_id,
        "command": req.command
    }

    # Push to the agent's queue
    r.rpush(f"queue:{req.agent_id}", str(payload))
    return {"status": "success", "task_id": task_id}

@app.get("/api/agent/task/{agent_id}")
def get_task(agent_id: str):
    if not r.sismember("agents", agent_id):
        raise HTTPException(status_code=404, detail="Agent not registered")

    queue_key = f"queue:{agent_id}"
    task_data = r.lpop(queue_key)

    if task_data:
        try:
            task_dict = ast.literal_eval(task_data)
            return task_dict
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to parse task payload")
    else:
        raise HTTPException(status_code=404, detail="No task")

@app.post("/api/agent/result")
def post_result(result: ResultRequest):
    key = f"result:{result.task_id}"
    r.set(key, result.output, ex=60)  # result expires after 60 seconds
    return {"status": "received"}
    
@app.get("/api/command/result/{task_id}")
def get_result(task_id: str):
    key = f"result:{task_id}"
    start_time = time.time()
    timeout = 10  # seconds

    while time.time() - start_time < timeout:
        if r.exists(key):
            result = r.get(key)
            r.delete(key)
            return {"status": "completed", "output": result}
        time.sleep(1)

    raise HTTPException(status_code=408, detail="Timeout waiting for result")
