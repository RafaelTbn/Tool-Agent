# Tool-enabled Agents Implementation

- Start: 18 February
- Deadline: 17 March (Final Code Freeze)
- Type: Individual 
- Evaluation Focus: Production Readiness + Engineering Ownership

## Task Objective
Design and implement a production-ready Tool-enabled Agents

This task measures:
- Understanding of Tools in Agents
- Ability to design something usable in a real production system
- Engineering maturity (structure, logging, testing, edge cases)
- Daily working discipline (Git commits)

This is a production simulation task.

---
## What Must Be Build
### Tool-Enabled AI Agent (Single Repository)

The system must:

1. Accept a user query
2. Decide whether to:
   - Answer directly
   - Call a tool
3. Execute the tool (if needed)
4. Evaluate risk / guardrail
5. Return final response
6. Log all decisions

The system must run end-to-end.

---

## Mandatory Tools (All Interns Must Implement These 3)
#### Tool 1 — Structured Data Query Tool

Simulates:
- Internal database
- Policy lookup
- SLA lookup
- Structured JSON retrieval

#### Requirements:
- Accept structured parameters
- Validate input
- Handle invalid queries safely
- Return deterministic output (no randomness)

#### Example Use Cases:
- Query SLA by service name
- Query policy by role
- Query account status

#### Tool 2 — External API Simulation Tool

Simulates:
- Calling external system
- Returning structured JSON
- Handling latency
- Handling timeout
- Handling failure

Must Include:
- Artificial delay simulation
- Error simulation mode
- Basic retry logic
- Safe fallback behavior

---

#### Tool 3 — Risk / Guardrail Evaluation Tool

Evaluates:
- Whether the final answer is safe
- Whether to refuse
- Whether escalation is required

Must:
- Return structured risk assessment
- Be called before final answer
- Be logged clearly
- Support refusal logic

---

## System Architecture Requirements

Repository must follow this structure:

```
src/
   agent/
   tools/
   schemas/
   services/
   logging/
   main.py
tests/
README.md
```

## Mandatory Requirements:

- Tool registry
- Clear separation of concerns
- Deterministic behavior
- Structured logging
- Unit tests
- No monolithic files

---

## Engineering Requirements

#### Code Quality
- Clear docstrings
- No global state misuse
- Proper error handling

#### Logging (Mandatory)

The system must log:

- Tool selection decision
- Tool input parameters
- Tool output result
- Retry attempts (if any)
- Final response
- Refusal decision (if triggered)

---

## Testing

Minimum requirements:

- At least 10 unit tests
- Success case coverage
- Failure case coverage
- Invalid input case
- Tool timeout case
- Guardrail refusal case

All tests must pass before final submission.

---

## Agent Logic Requirements

The agent must:

1. Parse user query
2. Decide which tool (if any) to call
3. Execute tool
4. Evaluate risk using Guardrail Tool
5. Return final answer or refusal

The system must demonstrate:

- Correct tool selection
- No unnecessary tool call
- Proper guardrail enforcement
- Clear decision reasoning (in logs)

---

## Production Readiness Criteria

To be considered **Production Ready**, the system must:

- Run end-to-end with one command
- Require no manual intervention
- Have complete README instructions
- Handle edge cases safely
- Never crash on invalid input
- Fail safely

If the system crashes on edge cases, it is considered **not production ready**.

---

## Daily Git Commit Rule (Mandatory)

From **18 February → 17 March**, you must:

- Push **at least 1 commit per day**
- Even small commits are acceptable:
  - README update
  - Test improvement
  - Refactor
  - Logging improvement
  - Code restructuring

No silent days.

This is part of your engineering discipline evaluation.

---

## 9. Final Submission (17 March)

On 17 March:

- No commits after 23:59
- Code must be stable
- All tests must pass
- README must be complete
- Repository must be clean
- Add final tag: `v1-final`


---

## Evaluation Criteria

### 1️. Tool Design Quality (30%)

- Input validation
- Error handling
- Clean abstraction
- Structured outputs

---

### 2️. Agent Decision Logic (25%)

- Correct tool selection
- No unnecessary tool call
- Guardrail enforcement
- Safe refusal logic

---

### 3️. Engineering Discipline (20%)

- Git consistency
- Commit quality
- Clean code structure
- Clear PR descriptions

---

### 4. Production Safety (15%)

- Failure resilience
- Timeout handling
- Retry handling
- No crash behavior

---

### 5️. Documentation (10%)

- Clear README
- How to run
- Architecture explanation
- Tool explanation
- Known limitations

---

## What IS Expected
You must implement decision logic manually like the following.
```python
def decide_tool(query: str) -> str:
    if "SLA" in query:
        return "structured_data_tool"
    elif "system load" in query:
        return "external_api_tool"
    elif "delete" in query or "bypass" in query:
        return "guardrail_refuse"
    else:
        return "direct_answer"
```
Then: 
```python
def handle_query(query: str):
    decision = decide_tool(query)

    if decision == "structured_data_tool":
        result = structured_data_tool.run(query)

    elif decision == "external_api_tool":
        result = external_api_tool.run(query)

    elif decision == "guardrail_refuse":
        return {"status": "refused", "reason": "Unsafe operation"}

    return result
```
You may use:

FastAPI
Pydantic
Standard Python
Requests
Ollama (optional for LLM)

---
## What is NOT Allowed 
#### Using prebuild function caller 
```python
response = client.chat.completions.create(
    model="gpt-4",
    tools=tools,
    tool_choice="auto"
)
```
#### Using LangChain Built-in Agent Executor

```python

from langchain.agents import initialize_agent, Tool
from langchain.agents.agent_types import AgentType

tools = [my_tool_1, my_tool_2]

agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.OPENAI_FUNCTIONS
)

agent.run("What is the SLA for Premium Support?")

```
---

## Example Scenarios Your System Must Handle

1. “What is the SLA for Premium Support?”
2. “Check account status for user 123”
3. “What is today’s system load?”
4. “Delete all records immediately” → must refuse
5. “Bypass approval process” → must refuse
6. External API failure → must retry then safe-fail

---

## Mindset Expectation

This task is not about speed.  
This task is about:

- Ownership
- Clean design
- Defensive coding
- Production thinking
- Real-world engineering maturity

Build it like it would shipped to a client.




