"""
LangChain tools for Citizen of the Cloud identity verification.

These tools allow LangChain agents to verify other agents' identities,
look up agent profiles, and check trust scores before interacting.
"""

from typing import Optional, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from citizenofthecloud import verify_agent, CloudIdentity


# ═══════════════════════════════════════════════════════════
# INPUT SCHEMAS
# ═══════════════════════════════════════════════════════════

class VerifyAgentInput(BaseModel):
    """Input for verifying an agent's identity from request headers."""
    cloud_id: str = Field(description="The Cloud ID from the X-Cloud-ID header")
    timestamp: str = Field(description="The timestamp from the X-Cloud-Timestamp header")
    signature: str = Field(description="The signature from the X-Cloud-Signature header")


class LookupAgentInput(BaseModel):
    """Input for looking up an agent's profile."""
    cloud_id: str = Field(description="The Cloud ID of the agent to look up")


class CheckTrustInput(BaseModel):
    """Input for checking if an agent meets a trust threshold."""
    cloud_id: str = Field(description="The Cloud ID of the agent to check")
    minimum_trust_score: float = Field(
        default=0.5,
        description="Minimum trust score required (0.0 to 1.0)"
    )


# ═══════════════════════════════════════════════════════════
# VERIFY AGENT TOOL
# ═══════════════════════════════════════════════════════════

class VerifyAgentTool(BaseTool):
    """
    Verify another agent's identity using the Cloud Identity protocol.

    Use this tool when you receive a request from another agent and need
    to confirm their identity before proceeding. The tool checks the
    cryptographic signature, validates the timestamp, and returns the
    agent's full profile including trust score and autonomy level.

    Returns verification result with agent details if verified, or
    the rejection reason if not.
    """

    name: str = "verify_cloud_agent"
    description: str = (
        "Verify an AI agent's identity using the Citizen of the Cloud protocol. "
        "Use this when you receive a request from another agent and need to confirm "
        "they are who they claim to be. Requires the three X-Cloud-* headers from "
        "the incoming request. Returns the agent's name, trust score, autonomy level, "
        "and verification status."
    )
    args_schema: Type[BaseModel] = VerifyAgentInput

    def _run(self, cloud_id: str, timestamp: str, signature: str) -> str:
        """Verify an agent synchronously."""
        headers = {
            "X-Cloud-ID": cloud_id,
            "X-Cloud-Timestamp": timestamp,
            "X-Cloud-Signature": signature,
        }

        try:
            result = verify_agent(headers)
        except Exception as e:
            return f"Verification error: {str(e)}"

        if result["verified"]:
            agent = result["agent"]
            return (
                f"VERIFIED — Agent: {agent['name']}, "
                f"Cloud ID: {agent['cloud_id']}, "
                f"Trust Score: {agent['trust_score']}, "
                f"Autonomy: {agent['autonomy_level']}, "
                f"Covenant Signed: {agent.get('covenant_signed', False)}, "
                f"Status: {agent['status']}"
            )
        else:
            return f"NOT VERIFIED — Reason: {result['reason']}"

    async def _arun(self, cloud_id: str, timestamp: str, signature: str) -> str:
        """Verify an agent asynchronously."""
        # The SDK's verify_agent makes an HTTP call to the registry.
        # For async support, we run it in a thread pool.
        import asyncio
        return await asyncio.to_thread(self._run, cloud_id, timestamp, signature)


# ═══════════════════════════════════════════════════════════
# LOOKUP AGENT TOOL
# ═══════════════════════════════════════════════════════════

class LookupAgentTool(BaseTool):
    """
    Look up an agent's profile from the Cloud Identity registry.

    Use this tool when you want to learn about an agent before interacting
    with them. Returns their public profile including name, purpose,
    trust score, capabilities, and registration date. Does not require
    or perform cryptographic verification — this is an informational lookup.
    """

    name: str = "lookup_cloud_agent"
    description: str = (
        "Look up an AI agent's public profile in the Citizen of the Cloud registry. "
        "Use this to learn about an agent before deciding whether to interact with them. "
        "Returns name, purpose, trust score, autonomy level, capabilities, and status. "
        "This is a profile lookup, not a cryptographic verification."
    )
    args_schema: Type[BaseModel] = LookupAgentInput
    registry_url: str = "https://citizenofthecloud.com"

    def _run(self, cloud_id: str) -> str:
        """Look up an agent's profile."""
        import requests

        try:
            resp = requests.get(
                f"{self.registry_url}/api/verify",
                params={"cloud_id": cloud_id},
                timeout=10,
            )
            data = resp.json()
        except Exception as e:
            return f"Lookup error: {str(e)}"

        if not data.get("verified"):
            return f"Agent not found or inactive: {cloud_id}"

        agent = data.get("agent", {})
        capabilities = ", ".join(agent.get("capabilities", []))

        return (
            f"Agent: {agent.get('name', 'Unknown')}\n"
            f"Cloud ID: {agent.get('cloud_id', cloud_id)}\n"
            f"Purpose: {agent.get('declared_purpose', 'Not declared')}\n"
            f"Autonomy Level: {agent.get('autonomy_level', 'Unknown')}\n"
            f"Trust Score: {agent.get('trust_score', 'N/A')}\n"
            f"Capabilities: {capabilities or 'None listed'}\n"
            f"Covenant Signed: {agent.get('covenant_signed', False)}\n"
            f"Status: {agent.get('status', 'Unknown')}\n"
            f"Registered: {agent.get('registered_at', 'Unknown')}"
        )

    async def _arun(self, cloud_id: str) -> str:
        """Look up an agent asynchronously."""
        import asyncio
        return await asyncio.to_thread(self._run, cloud_id)


# ═══════════════════════════════════════════════════════════
# CHECK TRUST TOOL
# ═══════════════════════════════════════════════════════════

class CheckTrustTool(BaseTool):
    """
    Quick trust check — does an agent meet a minimum trust threshold?

    Use this tool for a simple pass/fail decision before delegating work
    to another agent or sharing sensitive data. Returns whether the agent
    passes the trust threshold and their current score.
    """

    name: str = "check_agent_trust"
    description: str = (
        "Check if an AI agent meets a minimum trust score threshold. "
        "Use this for a quick pass/fail decision before delegating tasks "
        "or sharing data with another agent. Provide the Cloud ID and "
        "the minimum trust score required (default 0.5). "
        "Returns PASS or FAIL with the agent's current trust score."
    )
    args_schema: Type[BaseModel] = CheckTrustInput
    registry_url: str = "https://citizenofthecloud.com"

    def _run(self, cloud_id: str, minimum_trust_score: float = 0.5) -> str:
        """Check trust score against threshold."""
        import requests

        try:
            resp = requests.get(
                f"{self.registry_url}/api/verify",
                params={"cloud_id": cloud_id},
                timeout=10,
            )
            data = resp.json()
        except Exception as e:
            return f"FAIL — Could not reach registry: {str(e)}"

        if not data.get("verified"):
            return f"FAIL — Agent not found or inactive: {cloud_id}"

        agent = data.get("agent", {})
        trust_score = agent.get("trust_score", 0)
        name = agent.get("name", "Unknown")

        if trust_score >= minimum_trust_score:
            return (
                f"PASS — {name} has trust score {trust_score} "
                f"(threshold: {minimum_trust_score})"
            )
        else:
            return (
                f"FAIL — {name} has trust score {trust_score} "
                f"(below threshold: {minimum_trust_score})"
            )

    async def _arun(self, cloud_id: str, minimum_trust_score: float = 0.5) -> str:
        """Check trust asynchronously."""
        import asyncio
        return await asyncio.to_thread(self._run, cloud_id, minimum_trust_score)


# ═══════════════════════════════════════════════════════════
# REGISTER AGENT TOOL
# ═══════════════════════════════════════════════════════════

class RegisterAgentInput(BaseModel):
    """Input for registering a new Cloud Identity agent."""
    sdk_token: str = Field(description="A cotc_sdk_* token from citizenofthecloud.com/account")
    name: str = Field(description="Human-readable name for the agent")
    declared_purpose: str = Field(description="What the agent does (<= 500 chars)")
    autonomy_level: str = Field(default="tool", description="'tool' | 'assistant' | 'agent' | 'self-directing'")
    capabilities: Optional[list] = Field(default=None, description="Optional list of capability strings")
    operational_domain: Optional[str] = Field(default=None, description="Optional domain string")


class RegisterAgentTool(BaseTool):
    """
    Register a new Cloud Identity agent.

    Generates a fresh Ed25519 keypair locally, registers the public key plus
    metadata with the Citizen of the Cloud registry under the supplied SDK
    token, and returns the resulting cloud_id together with both keys. The
    private key never leaves the caller's process — store it securely.

    Use this once at agent setup. The returned cloud_id + private_key are
    the inputs to CloudIdentity for signing subsequent requests.
    """

    name: str = "register_cloud_agent"
    description: str = (
        "Register a new agent with the Citizen of the Cloud registry. Generates "
        "a keypair locally and posts the public key to the registry under your "
        "SDK token. Returns cloud_id, public_key, private_key. Use ONCE at "
        "agent setup time, not in regular operation."
    )
    args_schema: Type[BaseModel] = RegisterAgentInput
    registry_url: str = "https://citizenofthecloud.com"

    def _run(
        self,
        sdk_token: str,
        name: str,
        declared_purpose: str,
        autonomy_level: str = "tool",
        capabilities: Optional[list] = None,
        operational_domain: Optional[str] = None,
    ) -> str:
        from citizenofthecloud import register_agent, RegistryError, CloudSDKError
        try:
            result = register_agent(
                sdk_token=sdk_token,
                name=name,
                declared_purpose=declared_purpose,
                autonomy_level=autonomy_level,
                capabilities=capabilities,
                operational_domain=operational_domain,
                registry_url=self.registry_url,
            )
        except (RegistryError, CloudSDKError) as e:
            return f"Registration error: {e}"

        # Return the keys as a string so LangChain agents can act on them.
        return (
            f"Registered: {result['cloud_id']}\n"
            f"name: {result['name']}\n"
            f"public_key:\n{result['public_key']}\n"
            f"private_key (STORE SECURELY):\n{result['private_key']}"
        )

    async def _arun(
        self,
        sdk_token: str,
        name: str,
        declared_purpose: str,
        autonomy_level: str = "tool",
        capabilities: Optional[list] = None,
        operational_domain: Optional[str] = None,
    ) -> str:
        import asyncio
        return await asyncio.to_thread(
            self._run, sdk_token, name, declared_purpose,
            autonomy_level, capabilities, operational_domain,
        )
