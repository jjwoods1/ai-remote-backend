from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from redis import Redis
import os
import uuid
import time
import ast

app = FastAPI()

# Use Redis connection from full URL
REDIS_URL = os.getenv("REDISHOST", "redis://localhost:6379")
r = Redis.from_url(REDIS_URL, decode_responses=True)

class CommandRequest(BaseModel):
    agent_id: str
    command: str

@app.get("/")
def root():
    return {"message": "AI Remote Backend is running"}

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

    r.rpush(f"queue:{req.agent_id}", str(payload))
    return {"status": "success", "task_id": task_id}

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


