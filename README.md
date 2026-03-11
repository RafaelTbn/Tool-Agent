# Tool-Agent

Tool-enabled agent with deterministic tool routing plus a contextual SQL fallback layer.

## Run with Docker

Start Postgres and Ollama:

```bash
docker compose up -d
```

Pull any Ollama model manually after the container is running:

```bash
docker exec -it tool_agent_ollama ollama pull qwen2.5:3b
```

You can replace `qwen2.5:3b` with any model you want to try.

## Contextual fallback layer

If a query does not trigger the keyword-based decision rules, the agent:

1. searches the internal SQL data for a relevant record
2. if a record is found, sends the original query plus structured data to Ollama
3. if no record is found, falls back to the normal direct-answer path

Environment variables for the Ollama layer:

```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_TIMEOUT_SECONDS=30
```
