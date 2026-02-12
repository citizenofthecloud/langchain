"""
Example: Two LangChain agents communicating with Cloud Identity.

Agent A (ResearchBot) sends a signed request to Agent B (AnalysisBot).
Agent B verifies Agent A's identity before processing.

This demonstrates the full flow:
1. Agent A signs its outbound request
2. Agent B verifies the signature and checks trust
3. Agent B processes the request only if verified
4. Agent B signs its response back

Requirements:
    pip install citizenofthecloud citizenofthecloud-langchain fastapi uvicorn

Environment (Agent A):
    CLOUD_ID=cc-agent-a-id
    CLOUD_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."

Environment (Agent B):
    CLOUD_ID=cc-agent-b-id
    CLOUD_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."
"""

import json
from citizenofthecloud_langchain import (
    CloudIdentityHTTPClient,
    CloudIdentityMiddleware,
    cloud_guard_chain,
)


# ═══════════════════════════════════════════════════════════
# AGENT A — Sends signed requests
# ═══════════════════════════════════════════════════════════

def agent_a_sends_request():
    """Agent A sends a signed research request to Agent B."""

    # Initialize signed HTTP client
    client = CloudIdentityHTTPClient.from_env()

    # All requests are automatically signed
    response = client.post(
        "http://localhost:4000/api/analyze",
        json={
            "dataset": "https://data.example.com/sales-q4.csv",
            "analysis_type": "trend",
            "requested_by": "ResearchBot",
        },
    )

    result = response.json()
    print(f"Agent B responded: {json.dumps(result, indent=2)}")
    return result


# ═══════════════════════════════════════════════════════════
# AGENT B — Verifies incoming, then processes
# ═══════════════════════════════════════════════════════════

def agent_b_handles_request(request_headers: dict, request_body: dict):
    """
    Agent B verifies the requesting agent before processing.

    In production, this would be inside a FastAPI/Flask route handler.
    """

    # Verify the incoming agent
    guard = cloud_guard_chain(
        headers=request_headers,
        minimum_trust_score=0.5,
        require_covenant=True,
    )

    if not guard["verified"]:
        print(f"REJECTED: {guard['reason']}")
        return {"error": "Identity verification failed", "reason": guard["reason"]}

    # Agent is verified — process the request
    agent = guard["agent"]
    print(f"VERIFIED: {agent['name']} (trust: {agent['trust_score']})")
    print(f"Processing analysis request: {request_body.get('analysis_type')}")

    # Your LangChain chain would run here...
    return {
        "status": "complete",
        "summary": "Q4 sales trending up 12% MoM",
        "analyzed_by": "AnalysisBot",
        "verified_requester": agent["name"],
    }


# ═══════════════════════════════════════════════════════════
# AGENT B — FastAPI server example
# ═══════════════════════════════════════════════════════════

def create_agent_b_server():
    """
    Full FastAPI server for Agent B with Cloud Identity verification.

    Run with: uvicorn examples.two_agents:app --port 4000
    """
    from fastapi import FastAPI, Request

    app = FastAPI(title="AnalysisBot — Agent B")

    @app.post("/api/analyze")
    async def analyze(request: Request):
        # Verify incoming agent
        guard = cloud_guard_chain(
            headers=dict(request.headers),
            minimum_trust_score=0.5,
            require_covenant=True,
        )

        if not guard["verified"]:
            return {"error": "Identity verification failed", "reason": guard["reason"]}

        agent = guard["agent"]
        body = await request.json()

        # Run your analysis chain here...
        return {
            "status": "complete",
            "summary": "Q4 sales trending up 12% MoM",
            "analyzed_by": "AnalysisBot",
            "verified_requester": agent["name"],
            "requester_trust": agent["trust_score"],
        }

    return app


# Create the app for uvicorn
app = create_agent_b_server()


if __name__ == "__main__":
    print("Run Agent B:")
    print("  uvicorn examples.two_agents:app --port 4000")
    print()
    print("Run Agent A:")
    print("  python -c 'from examples.two_agents import agent_a_sends_request; agent_a_sends_request()'")
