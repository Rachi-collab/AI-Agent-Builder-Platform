import json
import httpx
import re
import time
from typing import Dict, Any, List, Optional, Generator, Tuple
from backend.models import AgentConfig, ReActStep, ChatMessage
from backend.tools import BaseTool, get_agent_tools

# System prompt template for the ReAct loop
SYSTEM_REACT_TEMPLATE = """You are an intelligent agent named {name}.
{description}

System Instructions:
{system_prompt}

You have access to the following tools:
{tools_description}

You must operate in a loop of Thought, Action, Action Input, and Observation.
To solve the task, use this exact format:

Thought: Describe your reasoning about the user request and what to do next.
Action: The name of the tool to use (must be one of: {tools_list}).
Action Input: The exact input arguments to pass to the tool.

The system will then run the tool and return the output as:
Observation: The output result of the tool execution.

You will repeat this cycle (Thought -> Action -> Action Input -> Observation) until you have enough information to answer.
Once you have the final answer, you must respond in this exact format:

Thought: I have gathered all necessary information to solve the user request.
Final Answer: [Your complete, detailed response to the user]

CRITICAL RULES:
1. Every turn MUST begin with "Thought:".
2. When calling a tool, you MUST output ONLY "Thought:", "Action:", and "Action Input:" blocks in that exact order. Do not write an Observation yourself.
3. When outputting the final answer, you MUST output "Thought:" followed by "Final Answer:".
4. Do not output anything else outside these blocks.
"""

def generate_tools_info(tools: Dict[str, BaseTool]) -> Tuple[str, str]:
    """Generates the tools description and list for the system prompt."""
    if not tools:
        return "No tools available.", "none"
    
    desc_list = []
    for name, tool in tools.items():
        desc_list.append(f"- {name}: {tool.description}")
        
    tools_description = "\n".join(desc_list)
    tools_list = ", ".join(tools.keys())
    return tools_description, tools_list

def parse_llm_response(text: str) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    """
    Parses LLM output for ReAct blocks: Thought, Action, Action Input, Final Answer.
    Returns (thought, action, action_input, final_answer).
    """
    thought = ""
    action = None
    action_input = None
    final_answer = None
    
    # Extract Thought
    thought_match = re.search(r'Thought:\s*(.*?)(?:Action:|Final Answer:|$)', text, re.DOTALL | re.IGNORECASE)
    if thought_match:
        thought = thought_match.group(1).strip()
    else:
        # Fallback: if no Thought prefix is found, treat the whole response as thought or text
        thought = text.strip()
        
    # Extract Action and Action Input
    action_match = re.search(r'Action:\s*([a-zA-Z0-9_\-]+)', text, re.IGNORECASE)
    action_input_match = re.search(r'Action Input:\s*(.*?)(?:Observation:|$)', text, re.DOTALL | re.IGNORECASE)
    
    if action_match:
        action = action_match.group(1).strip()
        if action_input_match:
            action_input = action_input_match.group(1).strip()
            # Remove bounding quotes if any
            action_input = re.sub(r'^[\'"]|[\'"]$', '', action_input)
            
    # Extract Final Answer
    final_match = re.search(r'Final Answer:\s*(.*)', text, re.DOTALL | re.IGNORECASE)
    if final_match:
        final_answer = final_match.group(1).strip()
        
    return thought, action, action_input, final_answer

def run_gemini_api(prompt: str, model: str, api_key: str, temperature: float) -> str:
    """Calls Gemini API directly using httpx."""
    # Maps common names to standard API model names
    model_name = "gemini-1.5-flash" if "flash" in model.lower() else "gemini-1.5-pro"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": temperature
        }
    }
    
    response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]

def run_openai_api(prompt: str, model: str, api_key: str, temperature: float) -> str:
    """Calls OpenAI chat completions API."""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model if model else "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature
    }
    
    response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]

def simulate_mock_llm(prompt: str, step_num: int, last_observation: Optional[str], active_tools: Dict[str, BaseTool]) -> str:
    """
    Simulates ReAct steps by analyzing the prompt/history.
    Allows testing full loop tool execution without API keys.
    """
    # Look for the user query at the bottom of the prompt
    # In our engine, we format history and then user query. Let's find what the user query is.
    query = ""
    lines = prompt.strip().split("\n")
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith("User:") or lines[i].startswith("Question:"):
            query = lines[i].split(":", 1)[1].strip()
            break
    if not query:
        query = lines[-1].strip()
        
    query_lower = query.lower()
    
    # Step 1: Initial call (no observation yet)
    if step_num == 0:
        # Check if calculator is available and requested
        if "calculator" in active_tools and any(op in query for op in ["+", "-", "*", "/", "%", "calculate", "math", "sum"]):
            # Extract possible mathematical expression
            expr_match = re.search(r'([0-9\+\-\*\/\(\)\.\s]{3,})', query)
            expr = expr_match.group(1).strip() if expr_match else "2 + 2"
            return f"Thought: The user wants me to compute a mathematical expression. I will use the calculator tool to evaluate '{expr}'.\nAction: calculator\nAction Input: {expr}"
            
        # Check if weather custom tool or general weather query
        if "weather" in query_lower:
            city_match = re.search(r'in ([a-zA-Z\s]+)', query)
            city = city_match.group(1).strip() if city_match else "Paris"
            tool_to_use = "web_search"
            for t in active_tools:
                if "weather" in t:
                    tool_to_use = t
                    break
            return f"Thought: The user is asking about the weather in {city}. I should check using my search/weather tool.\nAction: {tool_to_use}\nAction Input: weather in {city}"
            
        # Default fallback: search the web or fetch webpage if URL found
        url_match = re.search(r'(https?://[^\s]+)', query)
        if url_match and "web_fetch" in active_tools:
            return f"Thought: The user provided a URL. I should fetch the content of this webpage using the web_fetch tool.\nAction: web_fetch\nAction Input: {url_match.group(1)}"
            
        if "web_search" in active_tools:
            return f"Thought: The user is asking a general question. I will search the web for relevant information.\nAction: web_search\nAction Input: {query}"
            
        # No tools available or matched
        return f"Thought: I do not need any tools to answer this simple query.\nFinal Answer: Hello! I'm your AI Agent. I received your message: '{query}'. How can I assist you today?"
        
    # Step 2+: Subsequent calls (after tool execution)
    else:
        obs = last_observation or ""
        if "Error:" in obs:
            return f"Thought: The tool returned an error. I will report this to the user.\nFinal Answer: I attempted to execute the action but encountered an error:\n{obs}"
            
        # Process calculation result
        if "calculator" in prompt.lower() and re.match(r'^\-?[0-9\.]+$', obs.strip()):
            return f"Thought: The calculator tool returned {obs}. This resolves the query.\nFinal Answer: The calculation result is {obs}."
            
        # Process search results at step 1: fetch first link to show a multi-step loop
        if step_num == 1 and "web_search" in prompt.lower() and "web_fetch" in active_tools:
            # Look for a URL inside the search results
            url_match = re.search(r'URL:\s*(https?://[^\s\n\(\)]+)', obs)
            if url_match:
                url = url_match.group(1).strip()
                return f"Thought: The search results contain several links. I will fetch the full content of the primary resource '{url}' to extract deeper details.\nAction: web_fetch\nAction Input: {url}"
                
        # Fallback / step 2+: Compile final response from last observation
        summary_snippet = obs[:120].strip()
        if len(obs) > 120:
            summary_snippet += "..."
        return f"Thought: I have gathered details from the tool observation: '{summary_snippet}'. I can now construct the final response.\nFinal Answer: Based on my research and reading the retrieved source, here is the summary:\n\n{obs}"

def execute_react_loop(
    agent_config: AgentConfig,
    user_message: str,
    chat_history: List[ChatMessage],
    api_key: Optional[str] = None
) -> Generator[Dict[str, Any], None, None]:
    """
    Executes the ReAct loop generator, yielding logs of thoughts, actions, and observations.
    Yields dicts with format: {"type": "thought"|"action"|"observation"|"final_answer"|"error", "content": ...}
    """
    # 1. Setup tools
    active_tools = get_agent_tools(agent_config)
    tools_description, tools_list = generate_tools_info(active_tools)
    
    # 2. Build system instructions
    system_prompt = SYSTEM_REACT_TEMPLATE.format(
        name=agent_config.name,
        description=agent_config.description,
        system_prompt=agent_config.system_prompt,
        tools_description=tools_description,
        tools_list=tools_list
    )
    
    # 3. Assemble full prompt incorporating memory
    memory_messages = chat_history[-agent_config.memory_limit:] if agent_config.memory_limit > 0 else []
    
    # Assemble chat history text for the LLM
    history_str = ""
    for msg in memory_messages:
        role_label = "User" if msg.role == "user" else "Agent"
        history_str += f"{role_label}: {msg.content}\n"
        if msg.steps:
            for step in msg.steps:
                if step.thought:
                    history_str += f"Thought: {step.thought}\n"
                if step.action:
                    history_str += f"Action: {step.action}\nAction Input: {step.action_input}\nObservation: {step.observation}\n"
        history_str += "\n"
        
    base_prompt = f"{system_prompt}\n\nChat History:\n{history_str}Question: {user_message}\n"
    
    # Start loop
    max_iterations = 6
    current_prompt = base_prompt
    last_observation = None
    
    for i in range(max_iterations):
        yield {"type": "status", "content": f"Reasoning (Iteration {i+1})..."}
        
        try:
            # Query LLM (either live or mock)
            if agent_config.llm_provider == "gemini" and api_key:
                llm_response = run_gemini_api(current_prompt, agent_config.llm_model, api_key, agent_config.temperature)
            elif agent_config.llm_provider == "openai" and api_key:
                llm_response = run_openai_api(current_prompt, agent_config.llm_model, api_key, agent_config.temperature)
            else:
                # Use Mock simulation (which also calls actual tools)
                llm_response = simulate_mock_llm(current_prompt, i, last_observation, active_tools)
                # Sleep briefly to mimic thinking
                time.sleep(1.0)
                
        except Exception as e:
            yield {"type": "error", "content": f"LLM API Error: {str(e)}. Falling back to local Simulation mode."}
            # Fallback to simulation
            llm_response = simulate_mock_llm(current_prompt, i, last_observation, active_tools)
            time.sleep(1.0)
            
        # Parse output
        thought, action, action_input, final_answer = parse_llm_response(llm_response)
        
        # Yield Thought
        if thought:
            yield {"type": "thought", "content": thought}
            
        # If final answer, we are done
        if final_answer:
            yield {"type": "final_answer", "content": final_answer}
            return
            
        # If action, run tool
        if action:
            yield {"type": "action", "content": f"Tool: '{action}' | Input: '{action_input}'"}
            
            # Check if tool exists
            if action in active_tools:
                tool = active_tools[action]
                try:
                    # Execute tool
                    observation = tool.run(action_input or "")
                except Exception as e:
                    observation = f"Error executing tool '{action}': {str(e)}"
            else:
                observation = f"Error: Tool '{action}' is not available or registered."
                
            yield {"type": "observation", "content": observation}
            last_observation = observation
            
            # Append this step to prompt for next iteration
            current_prompt += f"\nThought: {thought}\nAction: {action}\nAction Input: {action_input}\nObservation: {observation}\n"
        else:
            # If LLM didn't choose an action and didn't provide a final answer, treat whole thing as final answer
            yield {"type": "final_answer", "content": thought}
            return
            
    # If we run out of iterations
    yield {"type": "final_answer", "content": "Limit of reasoning steps exceeded. Here is my partial response: I was unable to reach a final answer in time."}
