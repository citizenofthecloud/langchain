# citizenofthecloud-langchain

LangChain integration for the [Citizen of the Cloud](https://citizenofthecloud.com) identity protocol. Add cryptographic identity and trust verification to your LangChain agents.

## Install

This package is currently distributed directly from GitHub. The PyPI release is not yet caught up with the latest features (most recently: `RegisterAgentTool` and SDK-token auth). For now, install from GitHub:

```bash
git clone https://github.com/citizenofthecloud/langchain.git
pip install -e ./langchain
```

Or as a git dependency in `requirements.txt`:

```
citizenofthecloud-langchain @ git+https://github.com/citizenofthecloud/langchain.git@main
```

`pip` will also pull the [Citizen of the Cloud Python SDK](https://github.com/citizenofthecloud/sdk-python) — install that one from GitHub the same way for now (the published PyPI version is also behind).

> **Using LangChain in JavaScript / TypeScript?** This package is Python-only. See [LangChain.js users](#langchainjs-users) below — the recommended path is the MCP server, which works with both Python and JS LangChain.

## Quick Start

### 0. Register a New Agent (One-Time Setup)

If you don't already have an agent, the `RegisterAgentTool` creates one in a single call. Generates a fresh keypair locally, registers the public key with the registry under your SDK token, and returns the `cloud_id` + private key. Get a token from [citizenofthecloud.com/account](https://citizenofthecloud.com/account).

```python
from citizenofthecloud_langchain import RegisterAgentTool

tool = RegisterAgentTool()
result = tool.invoke({
    "sdk_token": "cotc_sdk_…",          # from /account
    "name": "My Research Bot",
    "declared_purpose": "Summarize papers and surface trends",
    "autonomy_level": "tool",
})
# result is a string containing cloud_id + public_key + private_key.
# Store the private_key securely — the server does not keep a copy.
```

Or invoke the underlying SDK function directly if you don't need the LangChain `BaseTool` wrapper:

```python
from citizenofthecloud import register_agent

agent = register_agent(
    sdk_token="cotc_sdk_…",
    name="My Research Bot",
    declared_purpose="Summarize papers and surface trends",
    autonomy_level="tool",
)
print(agent["cloud_id"])
print(agent["private_key"])   # store securely
```

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

## LangChain.js users

This package is Python-only. There is no `@citizenofthecloud/langchain` npm package today. LangChain.js users have two good options.

### Option 1 (recommended): consume the MCP server

The [Citizen of the Cloud MCP server](https://github.com/citizenofthecloud/mcp-server) exposes the full identity surface — verify, lookup, register, governance feed, the lot — as MCP tools. LangChain.js can consume any MCP server as a tool source via [`@langchain/mcp-adapters`](https://www.npmjs.com/package/@langchain/mcp-adapters), and you instantly get every MCP tool as a LangChain tool with no per-framework wrappers to maintain.

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
const tools = await client.getTools();   // verify-agent, register-agent, lookup-agent, ...

const agent = createReactAgent({
  llm: new ChatOpenAI({ model: 'gpt-4o' }),
  tools,
});
```

The same MCP server also works with Claude Desktop, Cursor, and every other MCP-aware client — so improvements to the MCP integration benefit every language and framework at once. This is the path we recommend for cross-language deployments.

### Option 2: wrap `@citizenofthecloud/sdk` directly

If you'd rather not run an MCP process, [`@citizenofthecloud/sdk`](https://github.com/citizenofthecloud/sdk-js) is the JS twin of `citizenofthecloud` (Python). It exposes `registerAgent`, `verifyAgent`, `lookupAgent`, `CloudIdentity`, etc. — same surface, same wire protocol. Wrap it in a LangChain.js tool with ~15 lines:

```ts
import { DynamicStructuredTool } from '@langchain/core/tools';
import { z } from 'zod';
import { registerAgent } from '@citizenofthecloud/sdk';

export const registerCloudAgentTool = new DynamicStructuredTool({
  name: 'register_cloud_agent',
  description:
    'Register a new agent with the Citizen of the Cloud registry. ' +
    'Generates a keypair locally and posts the public key under your SDK token.',
  schema: z.object({
    sdkToken: z.string().describe('cotc_sdk_* token from /account'),
    name: z.string(),
    declaredPurpose: z.string(),
    autonomyLevel: z.enum(['tool', 'assistant', 'agent', 'self-directing']).default('tool'),
  }),
  func: async ({ sdkToken, name, declaredPurpose, autonomyLevel }) => {
    const r = await registerAgent({ sdkToken, name, declaredPurpose, autonomyLevel });
    return JSON.stringify({ cloudId: r.cloudId, privateKey: r.privateKey });
  },
});
```

The same pattern works for `verifyAgent`, `lookupAgent`, and the rest of the sdk-js surface. Option 1 is still preferred for most users because the MCP server already does this wrapping once for every framework.

## Tools Reference

### RegisterAgentTool

One-shot agent registration. Generates a fresh Ed25519 keypair locally, posts the public key to `/api/register` under your SDK token, and returns the `cloud_id` together with both keys. The private key never leaves the caller's process — store it securely; the server keeps only the public key.

**When to use:** Bootstrap a new agent from code instead of clicking through the website. Use once at agent setup time, not in regular operation. Requires a `cotc_sdk_*` token from [/account](https://citizenofthecloud.com/account).

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
| `COTC_SDK_TOKEN` | Bootstrap SDK token (`cotc_sdk_*`) used by `RegisterAgentTool`. Get one from [citizenofthecloud.com/account](https://citizenofthecloud.com/account). |

## Links

- [Citizen of the Cloud](https://citizenofthecloud.com)
- [SDK Documentation](https://citizenofthecloud.com/docs)
- [Specification](https://citizenofthecloud.com/spec)
- [Python SDK](https://github.com/citizenofthecloud/sdk-python)
- [Register an Agent](https://citizenofthecloud.com/register)
