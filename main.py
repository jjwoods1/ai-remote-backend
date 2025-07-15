from fastapi import FastAPI
from redis import Redis

app = FastAPI()
r = Redis(host="localhost", port=6379, decode_responses=True)

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/api/agents/active")
def get_active_agents():
    agent_ids = r.smembers("active_agents")
    return {"active_agent_ids": list(agent_ids)}
