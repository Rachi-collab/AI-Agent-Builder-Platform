// Global State Variables
let agents = [];
let activeAgent = null;
let currentSessionId = "";

// DOM Elements
const agentListEl = document.getElementById("agent-list");
const agentSearchEl = document.getElementById("agent-search");
const btnNewAgent = document.getElementById("btn-new-agent");
const activeAgentTitle = document.getElementById("active-agent-title");
const activeAgentDesc = document.getElementById("active-agent-desc");
const tabPlaygroundBtn = document.getElementById("tab-playground-btn");

// Form Elements
const configForm = document.getElementById("agent-config-form");
const fieldAgentId = document.getElementById("field-agent-id");
const fieldAgentName = document.getElementById("field-agent-name");
const fieldAgentDesc = document.getElementById("field-agent-desc");
const fieldSystemPrompt = document.getElementById("field-system-prompt");
const fieldLlmProvider = document.getElementById("field-llm-provider");
const fieldLlmModel = document.getElementById("field-llm-model");
const fieldApiKey = document.getElementById("field-api-key");
const fieldTemp = document.getElementById("field-temperature");
const tempVal = document.getElementById("temp-val");
const fieldMemLimit = document.getElementById("field-memory-limit");
const apiKeyContainer = document.getElementById("api-key-container");
const fieldKnowledgeBase = document.getElementById("field-knowledge-base");

// Tools UI Elements
const toolCalculator = document.getElementById("tool-calculator");
const toolWebSearch = document.getElementById("tool-web-search");
const toolWebFetch = document.getElementById("tool-web-fetch");
const customToolsList = document.getElementById("custom-tools-list");
const btnAddCustomTool = document.getElementById("btn-add-custom-tool");

// Chat UI Elements
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const btnSendMessage = document.getElementById("btn-send-message");
const threadsList = document.getElementById("threads-list");
const btnNewSession = document.getElementById("btn-new-session");

// Console/Trace UI Elements
const consoleLogs = document.getElementById("console-logs");
const btnClearConsole = document.getElementById("btn-clear-console");

// Pipeline Status UI Elements
const indicatorDot = document.getElementById("indicator-dot");
const indicatorText = document.getElementById("indicator-text");
const pipeIdle = document.getElementById("pipe-idle");
const pipeThought = document.getElementById("pipe-thought");
const pipeAction = document.getElementById("pipe-action");
const pipeObservation = document.getElementById("pipe-observation");
const pipeFinished = document.getElementById("pipe-finished");

// Modal Elements
const customToolModal = document.getElementById("custom-tool-modal");
const customToolForm = document.getElementById("custom-tool-form");
const modalToolType = document.getElementById("modal-tool-type");
const modalToolMethod = document.getElementById("modal-tool-method");
const httpFieldsContainer = document.getElementById("http-fields-container");
const pythonCodeContainer = document.getElementById("python-code-container");
const bodyTemplateContainer = document.getElementById("body-template-container");
const closeModalBtn = document.querySelector(".close-modal");
const cancelModalBtn = document.querySelector(".close-btn");

// Startup setup
document.addEventListener("DOMContentLoaded", () => {
    initApp();
    setupEventHandlers();
});

// Initial load
async function initApp() {
    await fetchAgents();
    
    // Select the first agent if available
    if (agents.length > 0) {
        selectAgent(agents[0].id);
    } else {
        createNewAgentForm();
    }
}

// Set up DOM event handlers
function setupEventHandlers() {
    // Search filter
    agentSearchEl.addEventListener("input", filterAgents);
    
    // New Agent Button
    btnNewAgent.addEventListener("click", createNewAgentForm);
    
    // Temperature slider updating label
    fieldTemp.addEventListener("input", (e) => {
        tempVal.textContent = e.target.value;
    });
    
    // LLM Provider select - shows api key field if gemini or openai
    fieldLlmProvider.addEventListener("change", (e) => {
        const provider = e.target.value;
        if (provider === "mock") {
            apiKeyContainer.style.display = "none";
        } else {
            apiKeyContainer.style.display = "flex";
            if (provider === "gemini") {
                fieldApiKey.placeholder = "Enter Gemini API Key (AIzaSy...)";
            } else {
                fieldApiKey.placeholder = "Enter OpenAI API Key (sk-...)";
            }
        }
    });

    // Form submit
    configForm.addEventListener("submit", handleConfigSubmit);
    
    // Delete Agent button
    document.getElementById("btn-delete-agent").addEventListener("click", handleDeleteAgent);
    
    // Tabs switching
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const tabName = btn.getAttribute("data-tab");
            switchTab(tabName);
        });
    });
    
    // Send message triggers
    btnSendMessage.addEventListener("click", sendMessage);
    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            sendMessage();
        }
    });
    
    // Playground Thread Triggers
    btnNewSession.addEventListener("click", createNewSession);
    
    // Clear Console
    btnClearConsole.addEventListener("click", () => {
        consoleLogs.innerHTML = `
            <div class="console-placeholder">
                <i class="fa-solid fa-code-commit console-placeholder-icon"></i>
                <p>Console cleared. Reasoning logs will stream here on next run.</p>
            </div>
        `;
    });
    
    // Custom tool Modal handlers
    btnAddCustomTool.addEventListener("click", () => {
        customToolModal.style.display = "block";
        customToolForm.reset();
        modalToolType.dispatchEvent(new Event("change"));
    });
    
    modalToolType.addEventListener("change", (e) => {
        if (e.target.value === "python") {
            httpFieldsContainer.style.display = "none";
            pythonCodeContainer.style.display = "block";
        } else {
            httpFieldsContainer.style.display = "block";
            pythonCodeContainer.style.display = "none";
            modalToolMethod.dispatchEvent(new Event("change"));
        }
    });
    
    modalToolMethod.addEventListener("change", (e) => {
        if (modalToolType.value === "http" && (e.target.value === "POST" || e.target.value === "PUT")) {
            bodyTemplateContainer.style.display = "flex";
        } else {
            bodyTemplateContainer.style.display = "none";
        }
    });
    
    const closeModal = () => { customToolModal.style.display = "none"; };
    closeModalBtn.addEventListener("click", closeModal);
    cancelModalBtn.addEventListener("click", closeModal);
    window.addEventListener("click", (e) => {
        if (e.target === customToolModal) closeModal();
    });
    
    customToolForm.addEventListener("submit", handleAddCustomTool);
}

// Fetch lists
async function fetchAgents() {
    try {
        const response = await fetch("/api/agents");
        if (response.ok) {
            agents = await response.json();
            renderAgentList();
        }
    } catch (err) {
        console.error("Failed to load agents from API", err);
    }
}

// Render Sidebar List
function renderAgentList() {
    agentListEl.innerHTML = "";
    
    agents.forEach(agent => {
        const li = document.createElement("li");
        li.className = `agent-item ${activeAgent && activeAgent.id === agent.id ? 'active' : ''}`;
        li.innerHTML = `
            <div class="agent-item-name">
                <span>${agent.name}</span>
                <i class="fa-solid fa-chevron-right text-xs"></i>
            </div>
            <div class="agent-item-desc">${agent.description || 'No description'}</div>
        `;
        li.addEventListener("click", () => selectAgent(agent.id));
        agentListEl.appendChild(li);
    });
}

// Filter Sidebar List
function filterAgents(e) {
    const query = e.target.value.toLowerCase();
    const items = agentListEl.querySelectorAll(".agent-item");
    
    items.forEach((item, index) => {
        const name = agents[index].name.toLowerCase();
        const desc = (agents[index].description || "").toLowerCase();
        if (name.includes(query) || desc.includes(query)) {
            item.style.display = "block";
        } else {
            item.style.display = "none";
        }
    });
}

// Switch workspaces active tabs
function switchTab(tabId) {
    document.querySelectorAll(".tab-btn").forEach(btn => {
        if (btn.getAttribute("data-tab") === tabId) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });
    
    document.querySelectorAll(".tab-content").forEach(content => {
        if (content.id === tabId) {
            content.classList.add("active");
        } else {
            content.classList.remove("active");
        }
    });
}

// Select an active agent
async function selectAgent(agentId) {
    try {
        const response = await fetch(`/api/agents/${agentId}`);
        if (response.ok) {
            activeAgent = await response.json();
            
            // Set header labels
            activeAgentTitle.textContent = activeAgent.name;
            activeAgentDesc.textContent = activeAgent.description;
            
            // Populate configurations form
            fieldAgentId.value = activeAgent.id;
            fieldAgentName.value = activeAgent.name;
            fieldAgentDesc.value = activeAgent.description;
            fieldSystemPrompt.value = activeAgent.system_prompt;
            fieldLlmProvider.value = activeAgent.llm_provider;
            fieldLlmModel.value = activeAgent.llm_model;
            fieldTemp.value = activeAgent.temperature;
            tempVal.textContent = activeAgent.temperature;
            fieldMemLimit.value = activeAgent.memory_limit;
            
            // Load Knowledge Base documents text
            const kbDocs = activeAgent.knowledge_base || [];
            fieldKnowledgeBase.value = kbDocs.join("\n\n");
            
            // Trigger provider change to toggle API key container
            fieldLlmProvider.dispatchEvent(new Event("change"));
            
            // Populate built-in tools
            toolCalculator.checked = activeAgent.tools.includes("calculator");
            toolWebSearch.checked = activeAgent.tools.includes("web_search");
            toolWebFetch.checked = activeAgent.tools.includes("web_fetch");
            
            // Render custom tools list
            renderCustomToolsList();
            
            // Reset visual pipeline to idle
            setPipelineState("idle");
            
            // Session Setup - load multiple conversation threads for this agent
            await fetchAgentSessions(activeAgent.id);
            
            // Update active sidebar state
            renderAgentList();
        }
    } catch (err) {
        console.error("Failed to select agent", err);
    }
}

// Fetch all sessions/threads list for an agent
async function fetchAgentSessions(agentId) {
    try {
        const response = await fetch(`/api/agents/${agentId}/sessions`);
        if (response.ok) {
            const sessions = await response.json();
            
            if (sessions.length > 0) {
                // Render threads list and load the last active or first thread
                currentSessionId = sessions[sessions.length - 1];
                renderThreadsList(sessions);
                await fetchSessionHistory(currentSessionId);
            } else {
                // If agent has no conversations yet, initialize a new default one
                currentSessionId = `thread_${agentId}_${Date.now()}`;
                renderThreadsList([currentSessionId]);
                await fetchSessionHistory(currentSessionId);
            }
        }
    } catch (err) {
        console.error("Failed to load sessions list", err);
    }
}

// Render threads sidebar
function renderThreadsList(sessions) {
    threadsList.innerHTML = "";
    
    sessions.forEach((sessId, index) => {
        const li = document.createElement("li");
        li.className = `thread-item ${currentSessionId === sessId ? 'active' : ''}`;
        
        // Display a clean title for the thread
        const displayTitle = `Conversation #${index + 1}`;
        
        li.innerHTML = `
            <span><i class="fa-regular fa-message text-xs"></i> ${displayTitle}</span>
            <button class="btn-delete-thread" data-id="${sessId}" title="Delete Thread">
                <i class="fa-solid fa-trash-can text-xs"></i>
            </button>
        `;
        
        li.addEventListener("click", async (e) => {
            // Prevent switching if clicking delete
            if (e.target.closest(".btn-delete-thread")) return;
            currentSessionId = sessId;
            renderThreadsList(sessions);
            await fetchSessionHistory(currentSessionId);
        });
        
        li.querySelector(".btn-delete-thread").addEventListener("click", async (e) => {
            const targetId = e.currentTarget.getAttribute("data-id");
            if (confirm("Are you sure you want to delete this conversation thread?")) {
                await deleteSession(targetId);
            }
        });
        
        threadsList.appendChild(li);
    });
}

// Delete a session
async function deleteSession(sessionId) {
    try {
        const response = await fetch(`/api/sessions/${sessionId}`, { method: "DELETE" });
        if (response.ok) {
            // Refresh
            if (activeAgent) {
                await fetchAgentSessions(activeAgent.id);
            }
        }
    } catch (err) {
        console.error("Failed to delete session", err);
    }
}

// Create new blank conversation thread
async function createNewSession() {
    if (!activeAgent || !activeAgent.id) {
        alert("Please save your agent configuration first.");
        return;
    }
    
    currentSessionId = `thread_${activeAgent.id}_${Date.now()}`;
    chatMessages.innerHTML = "";
    renderChatPlaceholder();
    
    // Add current thread to UI lists
    if (activeAgent) {
        await fetchAgentSessions(activeAgent.id);
    }
}

// Get past chat history
async function fetchSessionHistory(sessionId) {
    chatMessages.innerHTML = "";
    try {
        const response = await fetch(`/api/sessions/${sessionId}`);
        if (response.ok) {
            const data = await response.json();
            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(msg => {
                    appendMessageBubble(msg.role, msg.content);
                });
            } else {
                renderChatPlaceholder();
            }
        } else {
            renderChatPlaceholder();
        }
    } catch (err) {
        renderChatPlaceholder();
    }
}

function renderChatPlaceholder() {
    chatMessages.innerHTML = `
        <div class="chat-placeholder">
            <i class="fa-regular fa-comments chat-placeholder-icon"></i>
            <h3>Start conversation with ${activeAgent ? activeAgent.name : 'Agent'}</h3>
            <p>Type your query below. All active tools will trigger dynamically.</p>
        </div>
    `;
}

// Create new empty configurations form
function createNewAgentForm() {
    activeAgent = null;
    activeAgentTitle.textContent = "Create New Agent";
    activeAgentDesc.textContent = "Set up your custom assistant instructions and tool accesses.";
    
    configForm.reset();
    fieldAgentId.value = "";
    tempVal.textContent = "0.7";
    apiKeyContainer.style.display = "none";
    fieldKnowledgeBase.value = "";
    
    // Set some defaults
    toolCalculator.checked = true;
    toolWebSearch.checked = true;
    toolWebFetch.checked = false;
    
    customToolsList.innerHTML = `<p class="no-items-text">No custom HTTP tools configured.</p>`;
    threadsList.innerHTML = "";
    chatMessages.innerHTML = `
        <div class="chat-placeholder">
            <i class="fa-regular fa-comments chat-placeholder-icon"></i>
            <h3>New Agent Playground</h3>
            <p>Save configuration settings first to enable interactive chats.</p>
        </div>
    `;
    
    switchTab("tab-builder");
    
    // Deselect list items
    document.querySelectorAll(".agent-item").forEach(item => item.classList.remove("active"));
}

// Save Config Submit
async function handleConfigSubmit(e) {
    e.preventDefault();
    
    const id = fieldAgentId.value;
    const name = fieldAgentName.value;
    const description = fieldAgentDesc.value;
    const system_prompt = fieldSystemPrompt.value;
    const llm_provider = fieldLlmProvider.value;
    const llm_model = fieldLlmModel.value;
    const temperature = parseFloat(fieldTemp.value);
    const memory_limit = parseInt(fieldMemLimit.value);
    
    // Tools
    const tools = [];
    if (toolCalculator.checked) tools.push("calculator");
    if (toolWebSearch.checked) tools.push("web_search");
    if (toolWebFetch.checked) tools.push("web_fetch");
    
    // Custom tools are loaded from the activeAgent if editing, or empty array if new agent
    const custom_tools = activeAgent ? activeAgent.custom_tools : [];
    
    // Parse Knowledge Base text documents
    const knowledge_base = fieldKnowledgeBase.value
        .split("\n\n")
        .map(doc => doc.trim())
        .filter(doc => doc.length > 0);
        
    const agentConfigPayload = {
        id: id || "",
        name,
        description,
        system_prompt,
        llm_provider,
        llm_model,
        temperature,
        memory_limit,
        tools,
        custom_tools,
        knowledge_base
    };
    
    try {
        const url = id ? `/api/agents/${id}` : "/api/agents";
        const method = id ? "PUT" : "POST";
        
        const response = await fetch(url, {
            method,
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(agentConfigPayload)
        });
        
        if (response.ok) {
            const saved = await response.json();
            // Refresh agents and select
            await fetchAgents();
            selectAgent(saved.id);
            alert("Agent configurations saved successfully!");
        } else {
            const errData = await response.json();
            alert(`Error saving configurations: ${errData.detail || 'Unknown error'}`);
        }
    } catch (err) {
        alert(`Failed to request config save: ${err.message}`);
    }
}

// Delete Agent
async function handleDeleteAgent() {
    const id = fieldAgentId.value;
    if (!id) {
        alert("Cannot delete an unsaved agent configuration.");
        return;
    }
    
    if (!confirm(`Are you sure you want to delete this agent? This action is permanent.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/agents/${id}`, {
            method: "DELETE"
        });
        if (response.ok) {
            alert("Agent deleted successfully.");
            initApp();
        } else {
            alert("Failed to delete agent.");
        }
    } catch (err) {
        alert(`Request failed: ${err.message}`);
    }
}

// Custom Tool Creation
function renderCustomToolsList() {
    customToolsList.innerHTML = "";
    
    if (!activeAgent || !activeAgent.custom_tools || activeAgent.custom_tools.length === 0) {
        customToolsList.innerHTML = `<p class="no-items-text">No custom tools added yet.</p>`;
        return;
    }
    
    activeAgent.custom_tools.forEach((tool, index) => {
        const card = document.createElement("div");
        card.className = "custom-tool-card-item";
        
        // Render customized badge for type
        const typeBadge = tool.tool_type === "python" 
            ? `<span class="badge badge-system">PYTHON</span>` 
            : `<span class="badge badge-warning">${tool.method}</span>`;
            
        card.innerHTML = `
            <div class="custom-tool-card-info">
                <h4>${tool.name} ${typeBadge}</h4>
                <p>${tool.description}</p>
            </div>
            <button type="button" class="btn-delete-tool" data-index="${index}" title="Remove Tool">
                <i class="fa-solid fa-trash-can"></i>
            </button>
        `;
        
        card.querySelector(".btn-delete-tool").addEventListener("click", (e) => {
            const idx = parseInt(e.currentTarget.getAttribute("data-index"));
            removeCustomTool(idx);
        });
        
        customToolsList.appendChild(card);
    });
}

function handleAddCustomTool(e) {
    e.preventDefault();
    
    const name = document.getElementById("modal-tool-name").value.trim();
    const description = document.getElementById("modal-tool-desc").value.trim();
    const tool_type = modalToolType.value;
    
    let newTool = {
        name,
        description,
        tool_type
    };
    
    if (tool_type === "python") {
        const python_code = document.getElementById("modal-tool-code").value;
        if (!python_code.includes("def run")) {
            alert("Python script must define a function 'def run(input_str):' returning a string value.");
            return;
        }
        newTool.python_code = python_code;
    } else {
        const method = modalToolMethod.value;
        const url = document.getElementById("modal-tool-url").value.trim();
        if (!url) {
            alert("URL endpoint is required for HTTP integration.");
            return;
        }
        const headersStr = document.getElementById("modal-tool-headers").value.trim();
        const body_template = document.getElementById("modal-tool-body").value.trim();
        
        // Parse headers JSON
        let headers = null;
        if (headersStr) {
            try {
                headers = JSON.parse(headersStr);
            } catch (err) {
                alert("Invalid JSON format in Headers. Please write valid JSON like: {\"Key\": \"Value\"}");
                return;
            }
        }
        
        newTool.method = method;
        newTool.url = url;
        newTool.headers = headers;
        newTool.body_template = body_template || null;
    }
    
    if (!activeAgent) {
        // Create a temporary mock agent configuration so we can add tools
        activeAgent = {
            id: "",
            name: fieldAgentName.value || "Temporary Agent",
            description: fieldAgentDesc.value || "",
            system_prompt: fieldSystemPrompt.value || "",
            llm_provider: fieldLlmProvider.value,
            llm_model: fieldLlmModel.value,
            temperature: parseFloat(fieldTemp.value),
            memory_limit: parseInt(fieldMemLimit.value),
            tools: [],
            custom_tools: [],
            knowledge_base: []
        };
    }
    
    activeAgent.custom_tools.push(newTool);
    renderCustomToolsList();
    customToolModal.style.display = "none";
}

function removeCustomTool(index) {
    if (activeAgent && activeAgent.custom_tools) {
        activeAgent.custom_tools.splice(index, 1);
        renderCustomToolsList();
    }
}

// Chat functions
function appendMessageBubble(role, content) {
    // Remove placeholder if present
    const placeholder = chatMessages.querySelector(".chat-placeholder");
    if (placeholder) {
        chatMessages.innerHTML = "";
    }
    
    const bubble = document.createElement("div");
    bubble.className = `message-bubble ${role}`;
    
    // Replace newlines with HTML breaks to preserve formatting
    bubble.innerHTML = content.replace(/\n/g, "<br>");
    
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Pipeline visualizer controls
function setPipelineState(state) {
    // Remove active class from all steps and connectors
    const steps = [pipeIdle, pipeThought, pipeAction, pipeObservation, pipeFinished];
    steps.forEach(step => step.classList.remove("active"));
    
    const connectors = document.querySelectorAll(".pipeline-connector");
    connectors.forEach(conn => conn.classList.remove("active"));
    
    // Reset indicator classes
    indicatorDot.className = "pulse-dot";
    
    switch (state) {
        case "idle":
            pipeIdle.classList.add("active");
            indicatorDot.classList.add("grey");
            indicatorText.textContent = "Agent is Idle";
            break;
            
        case "thought":
            pipeThought.classList.add("active");
            connectors[0].classList.add("active");
            indicatorDot.classList.add("orange");
            indicatorText.textContent = "Agent is thinking (ReAct)...";
            break;
            
        case "action":
            pipeAction.classList.add("active");
            connectors[0].classList.add("active");
            connectors[1].classList.add("active");
            indicatorDot.classList.add("purple");
            indicatorText.textContent = "Agent is executing a tool...";
            break;
            
        case "observation":
            pipeObservation.classList.add("active");
            connectors[0].classList.add("active");
            connectors[1].classList.add("active");
            connectors[2].classList.add("active");
            indicatorDot.classList.add("cyan");
            indicatorText.textContent = "Parsing tool output...";
            break;
            
        case "finished":
            pipeFinished.classList.add("active");
            connectors.forEach(conn => conn.classList.add("active"));
            indicatorDot.classList.add("green");
            indicatorText.textContent = "Task completed successfully!";
            break;
    }
}

// Main chat sender & EventStream processing
async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;
    
    if (!activeAgent || !activeAgent.id) {
        alert("Please save your agent configuration before querying the playground.");
        return;
    }
    
    chatInput.value = "";
    
    // Append user bubble
    appendMessageBubble("user", text);
    
    // Clear Console for fresh trace
    consoleLogs.innerHTML = "";
    
    // Set visual state to thinking
    setPipelineState("thought");
    
    // Switch to playground tab to show the terminal trace in real-time
    tabPlaygroundBtn.click();
    
    // Get active provider key
    const apiKey = fieldApiKey.value.trim() || null;
    
    // Build payload
    const payload = {
        agent_id: activeAgent.id,
        session_id: currentSessionId,
        message: text,
        api_key: apiKey
    };
    
    // Append typing bubble
    appendMessageBubble("assistant", "Thinking...");
    const bubbles = chatMessages.querySelectorAll(".message-bubble.assistant");
    const typingBubble = bubbles[bubbles.length - 1];
    
    try {
        const response = await fetch("/api/agents/run/stream", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            typingBubble.innerHTML = "Error: Failed to stream reasoning steps. Check terminal connection.";
            typingBubble.classList.add("error");
            setPipelineState("idle");
            return;
        }
        
        // Stream reading
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        
        let buffer = "";
        let finalAnswerText = "";
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            
            // Keep the last segment in buffer if incomplete
            buffer = lines.pop();
            
            for (const line of lines) {
                const cleanLine = line.trim();
                if (cleanLine.startsWith("data: ")) {
                    try {
                        const event = JSON.parse(cleanLine.slice(6));
                        processTraceEvent(event);
                        
                        if (event.type === "final_answer") {
                            finalAnswerText = event.content;
                        }
                    } catch (parseErr) {
                        console.error("Error parsing event line", cleanLine, parseErr);
                    }
                }
            }
        }
        
        // Replace typing bubble with the full final answer text
        if (finalAnswerText) {
            typingBubble.innerHTML = finalAnswerText.replace(/\n/g, "<br>");
        } else {
            typingBubble.innerHTML = "Completed run, but no final answer was extracted.";
        }
        
    } catch (err) {
        typingBubble.innerHTML = `Request Exception: ${err.message}`;
        typingBubble.classList.add("error");
        setPipelineState("idle");
        console.error(err);
    }
}

// Process single Trace Event to terminal logs
function processTraceEvent(event) {
    // Remove console placeholder if present
    const placeholder = consoleLogs.querySelector(".console-placeholder");
    if (placeholder) {
        consoleLogs.innerHTML = "";
    }
    
    const type = event.type;
    const content = event.content;
    
    // Update visual pipeline steps
    if (type === "thought") {
        setPipelineState("thought");
    } else if (type === "action") {
        setPipelineState("action");
    } else if (type === "observation") {
        setPipelineState("observation");
    } else if (type === "final_answer") {
        setPipelineState("finished");
        setTimeout(() => setPipelineState("idle"), 3500);
    } else if (type === "error") {
        setPipelineState("idle");
    }
    
    // Create console trace line
    const stepDiv = document.createElement("div");
    stepDiv.className = `log-step ${type}`;
    
    let title = type;
    if (type === "final_answer") title = "Final Answer";
    
    stepDiv.innerHTML = `
        <span class="log-title">${title}</span>
        <div class="log-content">${escapeHTML(content)}</div>
    `;
    
    consoleLogs.appendChild(stepDiv);
    consoleLogs.scrollTop = consoleLogs.scrollHeight;
}

// Helper to escape tags
function escapeHTML(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
