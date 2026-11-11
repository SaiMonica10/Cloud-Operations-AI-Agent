# Cloud Operations AI Agent

An AI agent that understands natural-language requests about cloud infrastructure, calls the right APIs, and returns clear answers.

## Stack
- **Python 3.10+**
- **FastAPI** — mock cloud API
- **OpenRouter** (via OpenAI SDK) — LLM with tool calling
- **httpx** — HTTP client for the agent
- **pytest** — testing

## Setup

**1. Create and activate virtual environment**
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Configure environment**
```bash
copy .env.example .env
```
Open `.env` and set your `OPENROUTER_API_KEY`.

## Running

**Terminal 1 — Start the mock API**
```bash
uvicorn mock_api.main:app --reload
```
Verify it works: open `http://localhost:8000/docs` in your browser.

**Terminal 2 — Run the agent**
```bash
# Interactive mode
python main.py

# Single question mode
python main.py "Find all stopped VMs inactive for more than 7 days"
```

## Demo Scenarios

**Scenario 1 — Stopped VMs inactive for 7+ days**
```
Find all stopped VMs in my project inactive for more than seven days
```

**Scenario 2 — VM status summary by project**
```
Give me a summary of all VM statuses in project-alpha
```

**Scenario 3 — Highest CPU usage**
```
Which VM is consuming the most CPU right now?
```

## Mock API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/vms` | List all VMs (`?status=stopped&project_id=project-alpha`) |
| GET | `/vms/{vm_id}` | Get a specific VM |
| GET | `/vms/{vm_id}/activity` | Get last activity timestamp |
| GET | `/projects` | List all projects |
| GET | `/projects/{project_id}/vms` | List VMs in a project |
| GET | `/metrics/{vm_id}` | Get CPU and memory metrics |
| GET | `/health` | Health check |

## Running Tests
```bash
pytest tests/ -v
```

## Project Structure
```
cloud-ops-agent/
├── mock_api/           # FastAPI mock cloud API
│   ├── data/           # Synthetic VM and project data
│   └── routers/        # API route handlers
├── agent/              # AI agent
│   ├── agent.py        # Main execution loop
│   ├── llm_client.py   # OpenRouter/LLM integration
│   ├── tools.py        # Tool definitions + dispatcher
│   ├── context.py      # Conversation history manager
│   └── tracer.py       # Execution trace logger
├── tests/              # Test suite
├── logs/traces/        # Execution traces (auto-created)
└── main.py             # CLI entry point
```
