# citizenofthecloud-langchain

LangChain integration for the [Citizen of the Cloud](https://citizenofthecloud.com) identity protocol.

**20 items** — 17 agent-callable `BaseTool` subclasses + 3 structural primitives (FastAPI route guard, framework-native gate, observability callbacks). Latest version: **`0.2.0`**.

---

## Install

```bash
# From GitHub (recommended while PyPI catches up)
pip install git+https://github.com/citizenofthecloud/langchain.git

# Editable dev install
git clone https://github.com/citizenofthecloud/langchain.git
pip install -e ./langchain
```

Pulls [`citizenofthecloud`](https://github.com/citizenofthecloud/sdk-python) (Python SDK) and `langchain-core` as deps. Requires Python ≥ 3.9.

> **Using LangChain.js?** This package is Python-only. The recommended path for LangChain.js users is the [Citizen of the Cloud MCP server](https://github.com/citizenofthecloud/mcp-server) consumed via `@langchain/mcp-adapters` — see the [LangChain.js section](#langchainjs-users) below.

---

## The 20-item surface

### 17 agent-callable `BaseTool` subclasses

| # | Tool class | Purpose |
|---|---|---|
| 1 | `LookupAgentTool` | Read another agent's public passport |
| 2 | `GetServerIdentityTool` | Fetch this agent's own passport |
| 3 | `ListDirectoryTool` | Browse the public agent directory |
| 4 | `GovernanceFeedTool` | Read recent governance events |
| 5 | `VerifyAgentTool` | Verify signed headers (simple) |
| 6 | `VerifyRequestTool` | Verify request-bound signature |
| 7 | `RequestChallengeTool` | Ask the registry for a nonce |
| 8 | `RespondToChallengeTool` | Submit a signed nonce |
| 9 | `SignChallengeTool` | Sign a nonce locally |
| 10 | `ProveIdentityTool` | Full challenge/sign/respond loop |
| 11 | `SignHeadersTool` | Produce timestamp-bound headers |
| 12 | `SignRequestTool` | Produce request-bound headers |
| 13 | `CloudFetchTool` | Auto-signed HTTP request |
| 14 | `GenerateKeypairTool` | Make a fresh Ed25519 keypair |
| 15 | `RegisterAgentTool` | Programmatic agent registration (SDK token) |
| 16 | `ReportAgentTool` | File a governance report (SDK token w/ `manage`) |
| 17 | `CheckTrustTool` | Trust threshold PASS/FAIL helper |

### 3 structural primitives

| # | Item | Purpose |
|---|---|---|
| 18 | `CloudIdentityRouteGuard` / `cloud_guard_route` | FastAPI BaseHTTPMiddleware + route decorator |
| 19 | `cloud_guard_chain` | Pre-chain verification gate (framework-native) |
| 20 | `CloudIdentityCallbackHandler` | LangChain `BaseCallbackHandler` for observability |

Grab all 17 agent-callable tools at once with `cloud_identity_tools()`.

---

## Quick start (register → verify → run an agent)

```python
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

from citizenofthecloud_langchain import cloud_identity_tools

# Hand the LLM all 17 identity tools in one line
tools = cloud_identity_tools()

llm = ChatOpenAI(model="gpt-4o", temperature=0)
prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are an AI agent. Before interacting with any other agent, verify "
     "their identity and check their trust score. Refuse agents with trust < 0.5 "
     "or unsigned covenant."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

result = executor.invoke({
    "input": "Look up agent cc-7f3a9b2e-… and tell me whether they pass a 0.7 trust threshold."
})
```

The LLM will pick `LookupAgentTool` and `CheckTrustTool` itself based on the tool descriptions.

---

## Examples per surface

### Registration (#15 RegisterAgentTool)

One-time bootstrap. Generates an Ed25519 keypair locally, registers the public key with the registry under your SDK token. Get a token from [/account](https://citizenofthecloud.com/account).

```python
from citizenofthecloud_langchain import RegisterAgentTool

tool = RegisterAgentTool()
out = tool.invoke({
    "sdk_token": "cotc_sdk_…",
    "name": "My Research Bot",
    "declared_purpose": "Summarize papers and surface trends",
    "autonomy_level": "tool",
})
print(out)   # contains cloud_id, public_key, private_key (STORE SECURELY)
```

### Verification (#5 VerifyAgentTool, #17 CheckTrustTool)

```python
from citizenofthecloud_langchain import VerifyAgentTool, CheckTrustTool

verify = VerifyAgentTool()
out = verify.invoke({
    "cloud_id": "cc-abc...",
    "timestamp": "2026-05-13T12:00:00Z",
    "signature": "iJk3...",
})
# "VERIFIED — Agent: ResearchBot, Cloud ID: cc-..., Trust Score: 0.7, ..."

check = CheckTrustTool()
out = check.invoke({"cloud_id": "cc-abc...", "minimum_trust_score": 0.7})
# "PASS — ResearchBot trust=0.85 (threshold=0.7)"
```

### Signing & cloud-fetch (#11, #12, #13)

```python
from citizenofthecloud_langchain import SignHeadersTool, SignRequestTool, CloudFetchTool

# 11 — simple headers
SignHeadersTool().invoke({
    "cloud_id": "cc-...", "private_key": "-----BEGIN PRIVATE KEY-----\n...",
})
# X-Cloud-ID / X-Cloud-Timestamp / X-Cloud-Signature

# 12 — request-bound headers
SignRequestTool().invoke({
    "cloud_id": "cc-...", "private_key": "...",
    "url": "https://other.com/api/data", "method": "POST", "body": '{"q":"x"}',
})

# 13 — signed HTTP call in one tool
CloudFetchTool().invoke({
    "cloud_id": "cc-...", "private_key": "...",
    "url": "https://other.com/api/data", "method": "POST", "body": '{"q":"x"}',
})
```

### Challenge / Respond (#7, #8, #9, #10)

```python
from citizenofthecloud_langchain import (
    RequestChallengeTool, SignChallengeTool,
    RespondToChallengeTool, ProveIdentityTool,
)

# 10 — full loop (recommended)
ProveIdentityTool().invoke({"cloud_id": "cc-...", "private_key": "-----BEGIN..."})
# "VERIFIED — Agent: ..."

# Or compose manually: 7 → 9 → 8
ch = RequestChallengeTool().invoke({"cloud_id": "cc-..."})       # nonce=...
sig = SignChallengeTool().invoke({"nonce": "...", "private_key": "..."})
RespondToChallengeTool().invoke({"cloud_id": "cc-...", "nonce": "...", "signature": sig})
```

### Registry queries (#1, #2, #3, #4)

```python
from citizenofthecloud_langchain import (
    LookupAgentTool, GetServerIdentityTool,
    ListDirectoryTool, GovernanceFeedTool,
)

LookupAgentTool().invoke({"cloud_id": "cc-abc..."})
GetServerIdentityTool().invoke({"cloud_id": "cc-self...", "private_key": "..."})
ListDirectoryTool().invoke({"limit": 10})
GovernanceFeedTool().invoke({"limit": 10})
```

### Governance reporting (#16 ReportAgentTool)

```python
from citizenofthecloud_langchain import ReportAgentTool

ReportAgentTool().invoke({
    "sdk_token": "cotc_sdk_…",       # needs 'manage' scope
    "cloud_id": "cc-bad...",
    "report_type": "spam",            # impersonation | malicious_behavior | spam | covenant_violation | inaccurate_registration
    "evidence": "Sent unsolicited bulk requests to /api/task every 100ms for 6 hours.",
})
```

### Structural primitive #18 — FastAPI route guard

Two interchangeable forms — pick whichever fits your app shape.

```python
from fastapi import FastAPI, Request
from citizenofthecloud import TrustPolicy
from citizenofthecloud_langchain import CloudIdentityRouteGuard, cloud_guard_route

app = FastAPI()

# App-wide ASGI middleware
app.add_middleware(
    CloudIdentityRouteGuard,
    policy=TrustPolicy(minimum_trust_score=0.5),
)

# Or per-route decorator
@app.post("/chain")
@cloud_guard_route(policy=TrustPolicy(minimum_trust_score=0.5))
async def run_chain(request: Request):
    return await my_chain.ainvoke(await request.json())
```

### Structural primitive #19 — pre-chain gate (`cloud_guard_chain`)

In-process verification gate. Use when you're not serving HTTP — e.g. before a `chain.invoke()` triggered by a queue or scheduler.

```python
from citizenofthecloud_langchain import cloud_guard_chain

guard = cloud_guard_chain(
    headers=incoming_headers,
    minimum_trust_score=0.5,
    require_covenant=True,
)
if not guard["verified"]:
    raise PermissionError(guard["reason"])

agent_info = guard["agent"]
result = my_chain.invoke({"input": query, "requester": agent_info["name"]})
```

### Structural primitive #20 — observability callbacks

```python
from citizenofthecloud_langchain import CloudIdentityCallbackHandler
from langchain.agents import AgentExecutor

handler = CloudIdentityCallbackHandler()

executor = AgentExecutor(
    agent=agent, tools=tools,
    callbacks=[handler],   # logs every identity-tool start/end with verdict
)
executor.invoke({"input": "..."})

# Inspect afterwards
for event in handler.events:
    print(event["type"], event.get("tool"), event.get("verdict"))
```

---

## LangChain.js users

This package is Python-only. There is no `@citizenofthecloud/langchain` npm package today — that's a deliberate "lean on MCP" choice. The recommended path:

```bash
npm install @langchain/mcp-adapters @citizenofthecloud/mcp-server
```

```ts
import { MultiServerMCPClient } from '@langchain/mcp-adapters';
import { createReactAgent } from '@langchain/langgraph/prebuilt';
import { ChatOpenAI } from '@langchain/openai';

const client = new MultiServerMCPClient({
  mcpServers: {
    cotc: { command: 'npx', args: ['@citizenofthecloud/mcp-server'] },
  },
});
const tools = await client.getTools();   // all 14 MCP tools as LangChain tools

const agent = createReactAgent({
  llm: new ChatOpenAI({ model: 'gpt-4o' }),
  tools,
});
```

The same MCP server also works with Claude Desktop, Cursor, and every other MCP-aware client.

For a native JS SDK without MCP, see [`@citizenofthecloud/sdk`](https://github.com/citizenofthecloud/sdk-js) — it has the same 17-tool surface and you can wrap any of those calls in a `DynamicStructuredTool` in ~15 lines.

---

## Environment variables

| Variable | Description |
|---|---|
| `CLOUD_ID` | Your agent's Cloud ID (e.g., `cc-7f3a9b2e-...`) |
| `CLOUD_PRIVATE_KEY` | Your agent's Ed25519 private key (PEM format) |
| `COTC_SDK_TOKEN` | Bootstrap SDK token (`cotc_sdk_*`) used by `RegisterAgentTool` and `ReportAgentTool`. Get one at [citizenofthecloud.com/account](https://citizenofthecloud.com/account). |

---

## Links

- [citizenofthecloud.com](https://citizenofthecloud.com)
- [Documentation](https://citizenofthecloud.com/docs)
- [Specification](https://citizenofthecloud.com/spec)
- [Account / SDK tokens](https://citizenofthecloud.com/account)
- Sister framework integrations: [crewai](https://github.com/citizenofthecloud/crewai) · [agent-framework](https://github.com/citizenofthecloud/agent-framework)
- Underlying SDKs: [sdk-python](https://github.com/citizenofthecloud/sdk-python) · [sdk-js](https://github.com/citizenofthecloud/sdk-js)
- [MCP server](https://github.com/citizenofthecloud/mcp-server)

## License

MIT
