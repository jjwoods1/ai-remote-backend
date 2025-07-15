from fastapi import FastAPI
from pydantic import BaseModel
from redis import Redis
import uuid

app = FastAPI()

# Redis connection (for local dev)
r = Redis(
    host=os.getenv("REDISHOST", "localhost"),
    port=int(os.getenv("REDISPORT", 6379)),
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True
)

# Root health check
@app.get("/")
def root():
    return {"status": "ok"}

# Agent registration
@app.post("/api/agent/register")
def register_agent():
    agent_id = str(uuid.uuid4())
    r.sadd("active_agents", agent_id)
    return {"agent_id": agent_id}

# Polling for commands (from agent)
class PollRequest(BaseModel):
    agent_id: str

@app.post("/api/agent/poll")
def poll_for_command(payload: PollRequest):
    command = r.lpop(f"agent:{payload.agent_id}:queue")
    return {"command": command}

# Sending commands (from operator to agent)
class CommandRequest(BaseModel):
    agent_id: str
    command: str

@app.post("/api/command/send")
def send_command(payload: CommandRequest):
    r.rpush(f"agent:{payload.agent_id}:queue", payload.command)
    return {"status": "queued"}

# List of active agents
@app.get("/api/agents/active")
def get_active_agents():
    agents = r.smembers("active_agents")
    return {"active_agent_ids": list(agents)}
