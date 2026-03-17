# Tool-Agent

Production-style tool-enabled AI agent with deterministic routing, structured tool outputs, guardrail evaluation, retry/timeout handling, contextual fallback, and structured logging.

## Overview

This project implements a single-repository tool-enabled agent that:

1. Accepts a user query
2. Decides whether to answer directly, call a tool, or refuse
3. Executes the tool when needed
4. Evaluates risk before returning the final answer
5. Logs the full decision flow

The implementation follows the repository structure required in [`ai_tools_task.md`](d:/Code/Pael/Tool-Agent/ai_tools_task.md).

## Repository Structure

```
├── data
│   └── internal_database_seed.sql
├── logs
│   └── agent_history.jsonl
├── src
│   ├── agent
│   │   ├── __init__.py
│   │   ├── agent_core.py
│   │   ├── decision_engine.py
│   │   ├── dependencies.py
│   │   └── response_utils.py
│   ├── logging
│   │   ├── __init__.py
│   │   └── logger.py
│   ├── schemas
│   │   ├── __init__.py
│   │   ├── request_schema.py
│   │   ├── response_schema.py
│   │   └── risk_schema.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── ollama_service.py
│   │   ├── retry_service.py
│   │   └── timeout_service.py
│   ├── tools
│   │   ├── external_api
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   ├── parser.py
│   │   │   └── tool.py
│   │   ├── structured_data
│   │   │   ├── __init__.py
│   │   │   ├── formatter.py
│   │   │   ├── matcher.py
│   │   │   ├── retriever.py
│   │   │   └── tool.py
│   │   ├── __init__.py
│   │   ├── external_api_tool.py
│   │   ├── guardrail_tool.py
│   │   ├── structured_data_tool.py
│   │   └── tool_registry.py
│   ├── __init__.py
│   ├── api.py
│   └── main.py
├── tests
│   ├── support.py
│   ├── test_agent_decision.py
│   ├── test_agent_orchestration.py
│   ├── test_logging.py
│   ├── test_tools_external_api.py
│   ├── test_tools_guardrail.py
│   └── test_tools_structured_data.py
├── .gitignore
├── README.md
├── ai_tools_task.md
├── docker-compose.yml
└── requirements.txt
```

## Implemented Tools

### 1. Structured Data Tool

Supports deterministic lookup against internal PostgreSQL-backed data for:
- SLA Lookup
- Policy Lookup
- Account Status Lookup
- Structured Fallback Retrieval

Key behaviors:
- Validates input
- Limits retrieval by relevant source group
- Returns structured JSON outputs
- Uses deterministic matching and ranking

### 2. External API Tool

Current external tool scope is weather lookup using Open-Meteo:
- Geocoding API
- Forecast API

Key behaviors:
- City-Level Location Extraction
- Retry Support
- Timeout Support
- Safe Fallback Response
- Rejects Unsupported Non-Weather External Queries Safely

### 3. Guardrail Tool

Evaluates:
- Unsafe Intent
- Refusal Requirement
- Escalation Requirement

Key behaviors:
- Structured Risk Output
- Refusal Logic
- Called Before Final Response

## Agent Flow

The agent flow is deterministic and manual, matching the task expectation:

1. Normalize and inspect the user query
2. Route to `guardrail_refuse`, `structured_data_tool`, `external_api_tool`, or `direct_answer`  
3. Execute the selected tool when needed
4. Optionally generate contextual answer text from tool data using Ollama
5. Evaluate response safety with the guardrail tool
6. Return the final structured response

## Architecture Notes

### Agent Layer

The Agent Layer Handles Decision Routing, Tool Orchestration, And Final Response Construction.

- [`src/agent/decision_engine.py`](d:/Code/Pael/Tool-Agent/src/agent/decision_engine.py): Implements Deterministic Tool Selection Rules
- [`src/agent/agent_core.py`](d:/Code/Pael/Tool-Agent/src/agent/agent_core.py): Coordinates The Main Agent Execution Flow
- [`src/agent/response_utils.py`](d:/Code/Pael/Tool-Agent/src/agent/response_utils.py): Builds Structured Responses And Contextual Answer Helpers

### Tool Layer

The Tool Layer Contains The Main Tool Implementations And The Registry Used To Wire Them Into The Agent.

- [`src/tools/structured_data`](d:/Code/Pael/Tool-Agent/src/tools/structured_data): Handles Internal Structured Lookup And Fallback Search
- [`src/tools/external_api`](d:/Code/Pael/Tool-Agent/src/tools/external_api): Handles External Weather API Requests
- [`src/tools/guardrail_tool.py`](d:/Code/Pael/Tool-Agent/src/tools/guardrail_tool.py): Evaluates Safety, Refusal, And Escalation
- [`src/tools/tool_registry.py`](d:/Code/Pael/Tool-Agent/src/tools/tool_registry.py): Registers And Resolves Tool Functions

### Services

The Services Layer Provides Shared Runtime Utilities Used Across The Agent And Tools.

- [`src/services/retry_service.py`](d:/Code/Pael/Tool-Agent/src/services/retry_service.py): Provides Deterministic Retry Handling
- [`src/services/timeout_service.py`](d:/Code/Pael/Tool-Agent/src/services/timeout_service.py): Enforces Timeout Thresholds
- [`src/services/ollama_service.py`](d:/Code/Pael/Tool-Agent/src/services/ollama_service.py): Wraps Contextual Answer Generation With Ollama

### Logging

The Logging Layer Captures Execution Events For Observability, Debugging, And History Tracking.

- [`src/logging/logger.py`](d:/Code/Pael/Tool-Agent/src/logging/logger.py): Emits Structured Logs To Terminal, Memory, And JSONL File

The logger:
- Prints structured logs to terminal
- Keeps in-memory history
- Writes persistent `.jsonl` logs to `logs/agent_history.jsonl`

## API Endpoints

### Health Check

`GET /health`

Returns:

```json
{
  "status": "ok"
}
```

### Query Endpoint

`POST /query`

Request:

```json
{
  "query": "What is SLA for Premium Support?",
  "include_debug": false
}
```

Response shape:

```json
{
  "status": "ok",
  "decision": "structured_data_tool",
  "message": "...",
  "risk": {
    "status": "approved",
    "risk_level": "low",
    "reason": "...",
    "escalation_required": false
  }
}
```

### Log History

`GET /logs`

Returns:
- In-Memory Log Entries
- Entry Count
- Log File Path
- Whether The JSONL File Exists

## How To Run

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Docker services

This starts PostgreSQL and Ollama:

```bash
docker compose up -d
```

### 3. Pull an Ollama model

```bash
docker exec -it tool_agent_ollama ollama pull qwen2.5:3b
```

You may replace `qwen2.5:3b` with another local model.

### 4. Run the API

```bash
uvicorn src.api:app --reload
```

### 5. Run from CLI

```bash
python -m src.main "What is SLA for Premium Support?"
```

## Environment Variables

### Ollama

```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_TIMEOUT_SECONDS=240
```

### Logging

```bash
AGENT_LOG_FILE=logs/agent_history.jsonl
```

### Database

The structured data tool reads:

```bash
DATABASE_URL=
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tool_agent
DB_USER=tool_user
DB_PASSWORD=tool_pass
DB_CONNECT_TIMEOUT=3
DB_SCHEMA=intern_task
```

## Testing

Run all tests:

```bash
python -m unittest discover -s tests -v
```

## Unit Test Coverage

The unit test suite validates the main behaviors of the system across multiple layers:

- **Agent Decision Tests**: Verify deterministic routing into structured data, external API, direct answer, and refusal paths.
- **Agent Orchestration Tests**: Verify end-to-end agent flow, including tool execution, contextual answer generation, debug payloads, and guardrail evaluation.
- **Structured Data Tool Tests**: Verify SLA lookup, policy lookup, account lookup, mixed-source retrieval, and fallback structured search behavior.
- **External API Tool Tests**: Verify weather query success flow, geocoding selection, retry handling, timeout fallback, and safe rejection of unsupported non-weather external queries.
- **Guardrail Tool Tests**: Verify safe approval and refusal logic for risky requests.
- **Logging Tests**: Verify in-memory log history and persistent JSONL log writing.


## Production Safety

This implementation includes:
- Deterministic decision logic
- Safe refusal handling
- Retry handling for external API calls
- Timeout handling
- Structured fallback behavior
- No-crash handling for invalid or unavailable tool results
- Persistent JSONL logging

## Known Limitations

- External API support is intentionally limited to weather queries
- Geocoding currently uses city-level extraction only
- Contextual answer generation depends on Ollama availability
- LLM-generated phrasing can vary unless fully constrained
- In-memory log history resets when the server process restarts
