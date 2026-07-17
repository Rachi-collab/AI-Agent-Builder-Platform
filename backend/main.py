import os
import json
import uuid
import time
import re
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional

from backend.models import AgentConfig, CustomToolConfig, ChatSession, ChatMessage, ReActStep, RunRequest
from backend.react_engine import execute_react_loop

app = FastAPI(title="AI Agent Builder Platform")

# CORS middleware for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories for persistence
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
AGENTS_DIR = os.path.join(DATA_DIR, "agents")
SESSIONS_DIR = os.path.join(DATA_DIR, "sessions")

for path in [DATA_DIR, AGENTS_DIR, SESSIONS_DIR]:
    os.makedirs(path, exist_ok=True)

# Helper functions for persistence
def save_agent(agent: AgentConfig):
    file_path = os.path.join(AGENTS_DIR, f"{agent.id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(agent.model_dump_json(indent=2))

def load_agents() -> List[AgentConfig]:
    agents = []
    for file_name in os.listdir(AGENTS_DIR):
        if file_name.endswith(".json"):
            file_path = os.path.join(AGENTS_DIR, file_name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    agents.append(AgentConfig(**data))
            except Exception:
                pass
    return agents

def get_agent_by_id(agent_id: str) -> Optional[AgentConfig]:
    file_path = os.path.join(AGENTS_DIR, f"{agent_id}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return AgentConfig(**data)
        except Exception:
            pass
    return None

def delete_agent_by_id(agent_id: str):
    file_path = os.path.join(AGENTS_DIR, f"{agent_id}.json")
    if os.path.exists(file_path):
        os.remove(file_path)

def save_session(session: ChatSession):
    file_path = os.path.join(SESSIONS_DIR, f"{session.session_id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(session.model_dump_json(indent=2))

def load_session(session_id: str) -> ChatSession:
    file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return ChatSession(**data)
        except Exception:
            pass
    return ChatSession(session_id=session_id, agent_id="")

# Create default agent templates if none exist
def create_default_agents():
    existing = load_agents()
    if not existing:
        templates = [
            AgentConfig(
                id="math-genius",
                name="Math Genius Agent",
                description="An expert in calculations, formulas, and math problem-solving.",
                system_prompt="Always show your steps. If you encounter a complex equation, break it down first.",
                llm_provider="mock",
                llm_model="gemini-1.5-flash",
                temperature=0.2,
                tools=["calculator"]
            ),
            AgentConfig(
                id="web-researcher",
                name="Research Assistant",
                description="Performs search engine lookup and text extraction to answer factual queries.",
                system_prompt="Be concise and reference search source snippets where appropriate. Make sure URLs are well formed.",
                llm_provider="mock",
                llm_model="gemini-1.5-flash",
                temperature=0.5,
                tools=["web_search", "web_fetch"]
            ),
            AgentConfig(
                id="all-rounder",
                name="Generalist Agent",
                description="Uses all tools to resolve general user queries and workflows.",
                system_prompt="Select the most appropriate tool to solve the question. Keep answer structures clean and clear.",
                llm_provider="mock",
                llm_model="gemini-1.5-flash",
                temperature=0.7,
                tools=["calculator", "web_search", "web_fetch"]
            )
        ]
        for agent in templates:
            save_agent(agent)

@app.on_event("startup")
def startup_event():
    create_default_agents()

# REST API Routes
@app.get("/api/agents", response_model=List[AgentConfig])
def api_list_agents():
    return load_agents()

@app.get("/api/agents/{agent_id}", response_model=AgentConfig)
def api_get_agent(agent_id: str):
    agent = get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@app.post("/api/agents", response_model=AgentConfig)
def api_create_agent(agent: AgentConfig):
    if not agent.id:
        agent.id = str(uuid.uuid4())
    save_agent(agent)
    return agent

@app.put("/api/agents/{agent_id}", response_model=AgentConfig)
def api_update_agent(agent_id: str, agent: AgentConfig):
    existing = get_agent_by_id(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.id = agent_id
    save_agent(agent)
    return agent

@app.delete("/api/agents/{agent_id}")
def api_delete_agent(agent_id: str):
    existing = get_agent_by_id(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Agent not found")
    delete_agent_by_id(agent_id)
    return {"status": "success", "message": f"Agent {agent_id} deleted."}

@app.get("/api/sessions/{session_id}", response_model=ChatSession)
def api_get_session(session_id: str):
    return load_session(session_id)

@app.post("/api/agents/run/stream")
def api_run_agent_stream(req: RunRequest):
    agent = get_agent_by_id(req.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    session = load_session(req.session_id)
    session.agent_id = agent.id
    
    # Append the user message to history
    user_msg = ChatMessage(role="user", content=req.message, timestamp=time.time())
    session.messages.append(user_msg)
    
    # We will build steps collection dynamically during streaming
    steps = []
    
    def event_generator():
        current_step = None
        assistant_content = ""
        
        # We pass in existing chat history (excluding the current user message itself)
        history_for_loop = session.messages[:-1]
        
        # Execute ReAct loop generator
        for event in execute_react_loop(agent, req.message, history_for_loop, req.api_key):
            event_type = event["type"]
            content = event["content"]
            
            # Formulate the response structure to send to SSE clients
            yield f"data: {json.dumps(event)}\n\n"
            
            # Capture step info to persist in database history
            if event_type == "thought":
                if current_step:
                    steps.append(current_step)
                current_step = ReActStep(thought=content)
            elif event_type == "action":
                # Split action/inputs for saving
                match = re.match(r"Tool:\s*'([^']*)'\s*\|\s*Input:\s*'([^']*)'", content)
                if match and current_step:
                    current_step.action = match.group(1)
                    current_step.action_input = match.group(2)
            elif event_type == "observation" and current_step:
                current_step.observation = content
            elif event_type == "final_answer":
                assistant_content = content
                if current_step:
                    steps.append(current_step)
                    current_step = None
                    
        # Append assistant response to session
        assistant_msg = ChatMessage(
            role="assistant",
            content=assistant_content,
            timestamp=time.time(),
            steps=steps
        )
        session.messages.append(assistant_msg)
        save_session(session)
        
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Serve UI static assets
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
os.makedirs(FRONTEND_DIR, exist_ok=True)

# Mount files if directory is not empty
@app.get("/")
def serve_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "AI Agent Builder Platform backend is running. Please construct index.html inside the frontend/ folder."}

app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")
