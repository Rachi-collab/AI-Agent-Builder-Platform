import json
import httpx
import uuid
from fastapi.testclient import TestClient
from backend.main import app

def test_rest_api_lifecycle():
    client = TestClient(app)
    
    # 1. Test listing default agents
    response = client.get("/api/agents")
    assert response.status_code == 200
    agents_list = response.json()
    assert len(agents_list) >= 3
    
    # Verify defaults exist
    agent_ids = [a["id"] for a in agents_list]
    assert "math-genius" in agent_ids
    assert "web-researcher" in agent_ids
    
    # 2. Test fetching a specific agent
    response = client.get("/api/agents/math-genius")
    assert response.status_code == 200
    agent = response.json()
    assert agent["name"] == "Math Genius Agent"
    assert "calculator" in agent["tools"]
    
    # 3. Test creating a new agent
    new_agent_data = {
        "id": "test-agent-123",
        "name": "Custom Test Agent",
        "description": "Formulated for tests",
        "system_prompt": "Answer briefly.",
        "llm_provider": "mock",
        "llm_model": "gemini-1.5-flash",
        "temperature": 0.4,
        "tools": ["calculator"],
        "memory_limit": 5,
        "custom_tools": []
    }
    response = client.post("/api/agents", json=new_agent_data)
    assert response.status_code == 200
    created = response.json()
    assert created["id"] == "test-agent-123"
    
    # 4. Verify created agent is retrieved
    response = client.get("/api/agents/test-agent-123")
    assert response.status_code == 200
    
    # 5. Clean up created agent
    response = client.delete("/api/agents/test-agent-123")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_react_streaming_endpoint():
    client = TestClient(app)
    session_id = f"session_test_{uuid.uuid4()}"
    
    # Let's send a run query to the Math Genius Agent
    run_payload = {
        "agent_id": "math-genius",
        "session_id": session_id,
        "message": "Calculate 34 * 8 + 5",
        "api_key": None
    }
    
    # Send post request to streaming route and read chunk responses
    events = []
    # TestClient in Starlette supports streaming responses using standard connection blocks
    with client.stream("POST", "/api/agents/run/stream", json=run_payload) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("data: "):
                event_data = json.loads(line[6:])
                events.append(event_data)
                
    # Verify that events contain the expected ReAct steps
    event_types = [e["type"] for e in events]
    
    # There should be status indicators, thoughts, tool executions, and final answer
    assert "status" in event_types
    assert "thought" in event_types
    assert "action" in event_types
    assert "observation" in event_types
    assert "final_answer" in event_types
    
    # Verify final answer structure
    final_answer = next(e["content"] for e in events if e["type"] == "final_answer")
    assert "277" in final_answer  # 34 * 8 + 5 = 272 + 5 = 277
    
    # Check that session history is saved properly
    history_response = client.get(f"/api/sessions/{session_id}")
    assert history_response.status_code == 200
    session_data = history_response.json()
    assert len(session_data["messages"]) == 2  # User message + assistant response
    assert session_data["messages"][0]["role"] == "user"
    assert session_data["messages"][1]["role"] == "assistant"
    # The assistant message should contain the parsed ReAct steps
    steps = session_data["messages"][1]["steps"]
    assert len(steps) > 0
    assert steps[0]["thought"] is not None

def test_react_research_agent_multi_step():
    client = TestClient(app)
    session_id = f"session_test_{uuid.uuid4()}"
    
    # We query the web-researcher agent to find information on Python creator
    run_payload = {
        "agent_id": "web-researcher",
        "session_id": session_id,
        "message": "Who created Python programming language? Perform a web search and fetch the page content.",
        "api_key": None
    }
    
    events = []
    with client.stream("POST", "/api/agents/run/stream", json=run_payload) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("data: "):
                event_data = json.loads(line[6:])
                events.append(event_data)
                
    event_types = [e["type"] for e in events]
    
    # It must execute web_search AND web_fetch
    actions = [e["content"] for e in events if e["type"] == "action"]
    assert any("web_search" in a for a in actions)
    assert any("web_fetch" in a for a in actions)
    
    # The final answer must contain "python" or "guido"
    final_answer = next(e["content"] for e in events if e["type"] == "final_answer")
    assert "python" in final_answer.lower()

