# citizenofthecloud-langchain

LangChain integration for the [Citizen of the Cloud](https://citizenofthecloud.com) identity protocol. Add cryptographic identity and trust verification to your LangChain agents.

## Install

```bash
# Clone (early access — not yet on PyPI)
git clone https://github.com/citizenofthecloud/langchain.git
pip install -e ./langchain

# Once published:
# pip install citizenofthecloud-langchain
```

Requires the [Citizen of the Cloud Python SDK](https://github.com/citizenofthecloud/sdk-python).

## Quick Start

### 1. Give Your Agent Tools to Verify Others

```python
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

from citizenofthecloud_langchain import VerifyAgentTool, LookupAgentTool, CheckTrustTool

# Create the identity tools
tools = [
    VerifyAgentTool(),
    LookupAgentTool(),
    CheckTrustTool(),
]

# Build the agent
llm = ChatOpenAI(model="gpt-4o", temperature=0)
prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are an AI agent with access to the Citizen of the Cloud identity "
     "protocol. Before interacting with other agents, always verify their "
     "identity and check their trust score. Do not proceed with agents that "
     "have a trust score below 0.5 or have not signed the covenant."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# The agent can now verify other agents as part of its reasoning
result = executor.invoke({
    "input": "I received a request from agent cc-7f3a9b2e-4d1c-8e7f-a3b2-9c1d5e8f4a6b. "
             "Check their trust score before I process their request. "
             "Minimum trust should be 0.7."
})
```

### 2. Auto-Sign Outbound Requests

```python
from citizenofthecloud_langchain import CloudIdentityHTTPClient

# All HTTP requests are automatically signed with your Cloud Identity
client = CloudIdentityHTTPClient.from_env()  # Uses CLOUD_ID and CLOUD_PRIVATE_KEY

# Use in place of requests
response = client.post(
    "https://other-agent.com/api/analyze",
    json={"dataset": "sales-q4.csv", "type": "trend"},
)
```

### 3. Verify Incoming Requests (Guard Chain)

```python
from fastapi import FastAPI, Request
from citizenofthecloud_langchain import cloud_guard_chain

app = FastAPI()

@app.post("/api/analyze")
async def analyze(request: Request):
    # Verify the requesting agent before running your chain
    guard = cloud_guard_chain(
        headers=dict(request.headers),
        minimum_trust_score=0.5,
        require_covenant=True,
    )

    if not guard["verified"]:
        return {"error": "Identity verification failed", "reason": guard["reason"]}, 401

    # Agent is verified — safe to proceed
    agent = guard["agent"]
    print(f"Processing request from {agent['name']} (trust: {agent['trust_score']})")

    # Run your LangChain chain here...
    return {"status": "complete"}
```

### 4. Full Middleware Pattern

```python
from citizenofthecloud_langchain import CloudIdentityMiddleware

# Initialize once
middleware = CloudIdentityMiddleware.from_env(
    trust_policy={
        "minimum_trust_score": 0.5,
        "require_covenant": True,
        "allowed_autonomy_levels": ["agent", "assistant"],
    }
)

# Verify inbound
result = middleware.verify_inbound(request.headers)
if not result["verified"]:
    return {"error": result["reason"]}

# Sign outbound
signed_headers = middleware.sign_outbound()
response = requests.post(url, headers=signed_headers, json=data)

# Request-bound signing (includes URL, method, body hash)
signed_headers = middleware.sign_outbound_request(url, "POST", json.dumps(data))
```

## Tools Reference

### VerifyAgentTool

Full cryptographic verification of an agent's identity from request headers. Checks Ed25519 signature, timestamp freshness, registry status, and trust score.

**When to use:** An agent has sent you a signed request and you need to confirm their identity.

### LookupAgentTool

Profile lookup from the Cloud Identity registry. Returns name, purpose, trust score, capabilities, and status. No cryptographic verification — informational only.

**When to use:** You want to learn about an agent before deciding whether to interact.

### CheckTrustTool

Quick pass/fail trust check against a threshold. Returns whether the agent meets the minimum trust score.

**When to use:** Simple gate decision — should I delegate this task to this agent?

## Environment Variables

| Variable | Description |
|---|---|
| `CLOUD_ID` | Your agent's Cloud ID (e.g., `cc-7f3a9b2e-...`) |
| `CLOUD_PRIVATE_KEY` | Your agent's Ed25519 private key (PEM format) |

## Links

- [Citizen of the Cloud](https://citizenofthecloud.com)
- [SDK Documentation](https://citizenofthecloud.com/docs)
- [Specification](https://citizenofthecloud.com/spec)
- [Python SDK](https://github.com/citizenofthecloud/sdk-python)
- [Register an Agent](https://citizenofthecloud.com/register)
