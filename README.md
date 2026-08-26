  # AI Agent Builder Platform
  
  An intelligent, full-stack **AI Agent Builder Platform** that enables users to visually design, configure, and execute custom autonomous agents. It implements a robust **ReAct (Reasoning and Action)** execution loop, supporting tool integration, short-term memory persistence, and real-time thought-process logging via Server-Sent Events (SSE).
  
  ---
  
  ## Features
  
  - **Dynamic ReAct Loop**: Seamlessly executes recursive *Thought ➔ Action ➔ Observation ➔ Thought* cycles until resolving user queries.
  - **Dual-Mode LLM Support**:
    - **Live Mode**: Direct raw HTTP endpoints to integrate **Google Gemini** or **OpenAI** APIs.
    - **Mock Mode**: A rule-based local interpreter allowing tool execution simulation and multi-step reasoning cycles completely offline (no API key required).
  - **Built-in Tool Library**:
    - **Math Calculator**: Secure math expression evaluator.
    - **Web Search**: Live search results via a DuckDuckGo HTML scraper.
    - **Web Fetcher**: Crawls webpage text, stripping CSS and scripts to return summary-ready text blocks.
  - **Custom API Tool Builder**: Design custom HTTP tools (GET, POST, PUT, DELETE) dynamically using visual templates (e.g., calling GitHub, weather, or custom endpoints).
  - **Trace Terminal**: Renders real-time reasoning logs in a beautiful console-like visual interface.
  - **File-based Persistence**: Saves agent templates and chat session logs locally.
  
  ---
  
  ## Architecture & Flow
  
  ```mermaid
  graph TD
      A[Web UI Dashboard] <-->|HTTP / Server-Sent Events| B[FastAPI Backend]
      B --> C[Agent Persistence Manager]
      B --> D[ReAct Engine Executor]
      C -->|Configs| E[(Local Data Store)]
      D -->|Executes| F[Tools / Scrapers]
      D -->|Queries| G[LLM API Router]
      F -->|Observation| D
      G -->|Response| D
  ```
  
  ---
  
  ## Tech Stack
  
  - **Backend**: Python 3, FastAPI, Uvicorn, Pydantic, HTTPX.
  - **Frontend**: HTML5, Vanilla CSS3 (custom dark/neon theme, glassmorphic grids), Vanilla JavaScript (Readable Stream API parser).
  - **Testing**: Pytest.
  
  ---
  
  ## Quick Start
  
  ### 1. Prerequisites
  Ensure you have **Python 3.8+** installed.
  
  ### 2. Setup Directory & Virtual Environment
  ```bash
  # Clone the repository
  git clone https://github.com/Rachi-collab/AI-Agent-Builder-Platform.git
  cd AI-Agent-Builder-Platform
  
  # Create a virtual environment
  python -m venv venv
  
  # Activate the environment
  # On Windows (PowerShell):
  .\venv\Scripts\Activate.ps1
  # On macOS/Linux:
  source venv/bin/activate
  ```
  
  ### 3. Install Dependencies
  ```bash
  pip install fastapi uvicorn httpx pytest jinja2
  ```
  
  ### 4. Start the Application
  ```bash
  python -m uvicorn backend.main:app --port 8000 --reload
  ```
  
  Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your web browser to access the dashboard.
  
  ---
  
  ## Running Tests
  
  A comprehensive suite of unit and integration tests is included. Run the following command:
  ```bash
  python -m pytest
  ```
  
  ---
  
  ## Usage Guide
  
  1. **Configure Your Agent**: Under the **Configuration** tab, give your agent a name, system prompt, select an LLM provider, and toggle access to built-in tools.
  2. **Create Custom Tools**: Click **Add API Tool** under the custom tools sidebar, specify the URL endpoint (using `{query}` for input injection), set headers, and select the HTTP method.
  3. **Save Agent**: Click **Save Configuration** to register the agent.
  4. **Playground**: Click the **Playground** tab and send a message. Watch the **ReAct Trace Stream** terminal on the right show the agent executing tools, evaluating data, and rendering results in real time!
