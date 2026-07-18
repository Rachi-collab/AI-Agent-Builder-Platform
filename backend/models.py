from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class CustomToolConfig(BaseModel):
    name: str
    description: str
    tool_type: str = "http"  # "http" or "python"
    url: Optional[str] = None
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    body_template: Optional[str] = None
    python_code: Optional[str] = None

class AgentConfig(BaseModel):
    id: str
    name: str
    description: str
    system_prompt: str
    llm_provider: str = "mock"  # "mock", "openai", "gemini"
    llm_model: str = "gemini-1.5-flash"
    temperature: float = 0.7
    tools: List[str] = []
    memory_limit: int = 10
    custom_tools: List[CustomToolConfig] = []
    knowledge_base: List[str] = []

class ReActStep(BaseModel):
    thought: str
    action: Optional[str] = None
    action_input: Optional[str] = None
    observation: Optional[str] = None

class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: float
    steps: Optional[List[ReActStep]] = None

class ChatSession(BaseModel):
    session_id: str
    agent_id: str
    messages: List[ChatMessage] = []

class RunRequest(BaseModel):
    agent_id: str
    session_id: str
    message: str
    api_key: Optional[str] = None
