
# coderClawLink

**A secure, distributed AI agent runtime — the execution backbone for [CoderClaw](https://github.com/SeanHogg/coderclaw).**

coderClawLink is the server-side orchestration engine that powers multi-agent AI development workflows. It provides a web portal, Telegram bot, and REST API for managing software projects, dispatching AI agents, and connecting to GitHub — all through a transport-agnostic runtime designed to scale from a single developer machine to an enterprise cluster.

When paired with [CoderClaw](https://github.com/SeanHogg/coderclaw), coderClawLink becomes the remote execution target: CoderClaw routes tasks from your messaging channels (Telegram, Slack, Discord, WhatsApp, etc.) through the `clawlink` transport adapter to this runtime, where agents do the actual work.

## 🎯 Vision

Modern software teams need AI that understands their codebase, not just their prompts. coderClawLink bridges the gap between conversational AI interfaces and real development work by providing:

- A **durable task engine** that tracks every agent action from submission to completion.
- A **transport abstraction layer** so tasks can arrive from any source — HTTP, WebSocket, CLI, or a connected CoderClaw gateway.
- An **enterprise-ready security model** with session isolation, RBAC, and comprehensive audit logging.
- **Deep GitHub integration** so agents can read repositories, create branches, and open pull requests without leaving the workflow.

## 🔄 How It Works

```
CoderClaw Gateway (Node.js)          coderClawLink (Python / FastAPI)
─────────────────────────────        ─────────────────────────────────────────
  Telegram / Slack / Discord   ───►  clawlink transport adapter
  WhatsApp / Signal / Teams          │
  WebChat / macOS / iOS              ├─► Session & RBAC validation
                                     ├─► Task state machine
                                     │     PENDING → PLANNING → RUNNING
                                     │     → WAITING → COMPLETED / FAILED
                                     │
                                     ├─► Agent Orchestrator
                                     │     ├─ Claude (Anthropic)
                                     │     ├─ Auggie (OpenAI)
                                     │     ├─ Ollama (local)
                                     │     ├─ OpenDevin
                                     │     └─ Goose
                                     │
                                     ├─► GitHub Integration
                                     │     ├─ Branch creation
                                     │     └─ Pull request automation
                                     │
                                     └─► Audit Log & Activity Trail
```

You can also use coderClawLink standalone — the web portal and Telegram bot work independently of CoderClaw.

## ✨ Key Capabilities

### 🖥️ Web Portal & Kanban Board
A modern project management UI with drag-and-drop Kanban boards (To Do → In Progress → In Review → Done). Create projects, assign tasks to agents, and watch progress in real time.

### 📱 Telegram Bot
Interact with projects and agents entirely from Telegram. Create tasks, trigger agent execution, and receive results without opening a browser.

### 🤖 Multi-Agent Orchestration
Dispatch work to the right model for the job:
- 🧠 **Claude** (Anthropic) — long-context reasoning and code generation
- 🤖 **Auggie** (OpenAI) — GPT-powered task execution
- 🦙 **Ollama** — run any model locally with full privacy
- 🔨 **OpenDevin** — autonomous software engineering agent
- 🦆 **Goose** — code-focused AI assistant

### 🔌 Transport Abstraction Layer
A pluggable adapter pattern decouples task submission from transport protocol. The same runtime serves local in-process calls, HTTP requests, WebSocket streams, and the CoderClaw `clawlink` adapter — no code changes required when switching transports.

### 🔗 GitHub Integration
Link any project to a GitHub repository. Agents can create feature branches and open pull requests automatically as part of a task workflow.

### 🔐 Security & Compliance
- Multi-session isolation with UUID-keyed sessions
- Role-based access control (admin, developer, readonly, ci)
- Device trust levels (trusted, verified, untrusted)
- Comprehensive audit log covering every session, task, and security event

## 🔌 CoderClaw Integration

[CoderClaw](https://github.com/SeanHogg/coderclaw) is a developer-first, multi-channel AI gateway. It connects to the messaging platforms you already use and routes conversations to AI agents. coderClawLink is the backend those agents execute against.

### How the integration works

1. **Install and configure CoderClaw** on your machine or server.
2. **Run coderClawLink** to expose the runtime API.
3. **Configure the `clawlink` transport** in CoderClaw to point at your coderClawLink endpoint.
4. **Send messages** from Telegram, Slack, Discord, or any other connected channel — CoderClaw routes them through the clawlink adapter to coderClawLink, which dispatches the right agent, tracks the task lifecycle, and returns the result.

```bash
# In CoderClaw — point the clawlink transport at coderClawLink
coderclaw gateway --port 18789 --verbose

# Then from any connected channel:
@coderclaw create a login component for the ACME project
# → CoderClaw routes this → coderClawLink → Claude agent → GitHub PR
```

### What CoderClaw provides
- Multi-channel inbox (WhatsApp, Telegram, Slack, Discord, Google Chat, Signal, iMessage, Teams, Matrix, WebChat, and more)
- Voice wake and talk mode on macOS/iOS/Android
- Session and channel routing
- Live Canvas for visual agent output

### What coderClawLink provides
- Durable task execution with full state machine
- Agent orchestration (Claude, Auggie, Ollama, OpenDevin, Goose)
- GitHub repository and PR management
- Session-scoped RBAC and audit logging
- REST API for direct integration

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Git
- (Optional) Telegram Bot Token — from [@BotFather](https://t.me/BotFather)
- (Optional) GitHub personal access token
- (Optional) API keys for AI agents (Anthropic, OpenAI, etc.)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/SeanHogg/coderClawLink.git
cd coderClawLink
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create and configure your `.env` file:
```bash
cp .env.example .env
```

```env
# Database
DATABASE_URL=sqlite+aiosqlite:///./portal.db

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# GitHub
GITHUB_TOKEN=your_github_token_here

# Agent API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Ollama (if running locally)
OLLAMA_BASE_URL=http://localhost:11434

# Server
API_HOST=0.0.0.0
API_PORT=8000
```

4. Start the server:
```bash
python -m app.main
```

5. Open the portal at `http://localhost:8000`

Interactive API docs are available at `http://localhost:8000/docs`.

### Typical Workflow

```
1. Create a project  →  link it to a GitHub repository
2. Create a task     →  describe what needs to be done
3. Execute           →  pick an agent (claude, auggie, ollama, …)
4. Review results    →  agent output + optional GitHub PR
```

From Telegram:
```
/create_project DEMO "My App"
/create_task DEMO "Implement login feature"
/execute DEMO-1 claude
```

From the REST API:
```python
import requests

# Create a session
session = requests.post("http://localhost:8000/api/runtime/sessions", json={
    "user_id": "user@example.com",
    "device_id": "my-laptop"
}).json()

# Submit a task
task = requests.post("http://localhost:8000/api/runtime/tasks/submit", json={
    "agent_type": "claude",
    "prompt": "Create a login component",
    "session_id": session["session_id"],
    "context": {"project": "DEMO"}
}).json()

# Poll for completion
state = requests.get(f"http://localhost:8000/api/runtime/tasks/{task['task_id']}/state").json()
print(state["state"])  # COMPLETED
```

## 📊 API Reference

### Project & Task Management
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/projects` | List all projects |
| `POST` | `/api/projects` | Create a project |
| `GET` | `/api/tasks` | List tasks |
| `POST` | `/api/tasks` | Create a task |
| `POST` | `/api/tasks/execute` | Execute a task with an agent |
| `POST` | `/api/tasks/{id}/create_pr` | Open a GitHub PR for a task |
| `GET` | `/api/agents/available` | List configured agents |

### Distributed Runtime
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/runtime/sessions` | Create a session |
| `GET` | `/api/runtime/sessions/{id}` | Get session info |
| `POST` | `/api/runtime/tasks/submit` | Submit a task |
| `GET` | `/api/runtime/tasks/{id}/state` | Query task state |
| `POST` | `/api/runtime/tasks/{id}/cancel` | Cancel a task |
| `GET` | `/api/runtime/agents` | List available agents |
| `GET` | `/api/runtime/skills` | List available skills |

### Audit & Compliance
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/audit/events` | Query audit events (admin) |
| `GET` | `/api/audit/users/{id}/activity` | User activity history |
| `GET` | `/api/audit/sessions/{id}/activity` | Session activity |

## 🏗️ Project Structure

```
app/
├── agents/              # Agent implementations
│   ├── base.py          # Base agent interface
│   ├── claude_agent.py
│   ├── ollama_agent.py
│   ├── openai_agent.py
│   ├── http_agent.py
│   └── orchestrator.py
├── api/                 # FastAPI route handlers
│   ├── projects.py
│   ├── tasks.py
│   ├── agents.py
│   ├── runtime.py       # Distributed runtime endpoints
│   └── audit.py         # Audit log endpoints
├── core/
│   ├── config.py
│   └── database.py
├── github_integration/
│   └── client.py
├── models/
│   ├── database.py
│   └── schemas.py
├── security/
│   ├── session.py       # Multi-session isolation
│   ├── rbac.py          # Role-based access control
│   └── audit.py         # Audit logging
├── transport/
│   ├── interface.py     # Runtime interface contract
│   └── local_runtime.py # Local adapter implementation
├── static/              # Web portal assets
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── telegram_bot/
│   └── bot.py
└── main.py
```

## 🛠️ Development

### Running Tests

```bash
pip install pytest pytest-asyncio
pytest
```

### Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for Docker, systemd, and Nginx configuration.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## 💬 Support
