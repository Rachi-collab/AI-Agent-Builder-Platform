import pytest
from backend.react_engine import parse_llm_response, generate_tools_info
from backend.tools import CalculatorTool, SerpSearchTool, WebFetchTool, get_agent_tools
from backend.models import AgentConfig

def test_parse_llm_response_thought_action():
    text = "Thought: I need to calculate this expression.\nAction: calculator\nAction Input: 12 + 34"
    thought, action, action_input, final_answer = parse_llm_response(text)
    
    assert thought == "I need to calculate this expression."
    assert action == "calculator"
    assert action_input == "12 + 34"
    assert final_answer is None

def test_parse_llm_response_final_answer():
    text = "Thought: I have the calculation results.\nFinal Answer: The final result is 46."
    thought, action, action_input, final_answer = parse_llm_response(text)
    
    assert thought == "I have the calculation results."
    assert action is None
    assert action_input is None
    assert final_answer == "The final result is 46."

def test_parse_llm_response_fallback():
    text = "Just a general comment without prefix blocks"
    thought, action, action_input, final_answer = parse_llm_response(text)
    
    assert thought == "Just a general comment without prefix blocks"
    assert action is None
    assert action_input is None
    assert final_answer is None

def test_generate_tools_info():
    tools = {
        "calculator": CalculatorTool(),
        "web_search": SerpSearchTool()
    }
    desc, names = generate_tools_info(tools)
    
    assert "calculator" in names
    assert "web_search" in names
    assert "calculator" in desc
    assert "web_search" in desc

def test_get_agent_tools():
    config = AgentConfig(
        id="test-agent",
        name="Test",
        description="Desc",
        system_prompt="System",
        tools=["calculator", "web_search"]
    )
    tools = get_agent_tools(config)
    assert "calculator" in tools
    assert "web_search" in tools
    assert "web_fetch" not in tools

def test_knowledge_retrieval_tool():
    from backend.tools import KnowledgeRetrievalTool
    docs = [
        "Tokyo is the capital of Japan.",
        "Python was designed by Guido van Rossum and released in 1991."
    ]
    tool = KnowledgeRetrievalTool(docs)
    
    # Check match for query containing designed/Guido
    res1 = tool.run("Who designed python?")
    assert "Guido van Rossum" in res1
    assert "Result [1]" in res1
    
    # Check query for Tokyo
    res2 = tool.run("What is the capital of Japan?")
    assert "Tokyo" in res2
    
    # Check query returning nothing
    res3 = tool.run("Something completely random")
    assert "No relevant facts found" in res3

def test_python_script_tool_valid():
    from backend.tools import PythonScriptTool
    code = """
def run(input_val):
    import math
    return f"Square root of {input_val} is {math.sqrt(float(input_val))}"
"""
    tool = PythonScriptTool("test_code", "test", code)
    res = tool.run("16")
    assert "Square root of 16 is 4.0" in res

def test_python_script_tool_sandbox_restricted():
    from backend.tools import PythonScriptTool
    # Try using blocked builtin/module import
    code = """
def run(input_val):
    import os
    return str(os.listdir('.'))
"""
    tool = PythonScriptTool("test_code", "test", code)
    res = tool.run("")
    # It should raise an error message during execution
    assert "Error" in res
