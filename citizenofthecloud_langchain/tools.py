"""
LangChain tools for Citizen of the Cloud identity verification.

Full 17 agent-callable tools (the framework target surface excludes only
the 3 structural primitives — middleware / native gate / callbacks — which
live in their own modules).
"""

from typing import Optional, Type, List
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from citizenofthecloud import (
    verify_agent,
    verify_request,
    generate_key_pair,
    cloud_fetch,
    request_challenge,
    submit_challenge_response,
    lookup_agent,
    list_directory,
    get_governance_feed,
    register_agent,
    CloudIdentity,
)

# Canonical host is www. The bare apex 307-redirects here, and HTTP
# clients strip the Authorization header on cross-host redirects — so
# callers using the bare apex silently fail register_agent with a 401.
DEFAULT_REGISTRY = "https://www.citizenofthecloud.com"


# ──────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────

def _fmt_agent(agent: dict) -> str:
    """Format an agent dict for human-readable tool output."""
    caps = ", ".join(agent.get("capabilities") or []) or "None listed"
    return (
        f"Agent: {agent.get('name', 'Unknown')}\n"
        f"Cloud ID: {agent.get('cloud_id', 'Unknown')}\n"
        f"Purpose: {agent.get('declared_purpose', 'Not declared')}\n"
        f"Autonomy: {agent.get('autonomy_level', 'Unknown')}\n"
        f"Trust Score: {agent.get('trust_score', 'N/A')}\n"
        f"Capabilities: {caps}\n"
        f"Covenant Signed: {agent.get('covenant_signed', False)}\n"
        f"Status: {agent.get('status', 'Unknown')}"
    )


# ──────────────────────────────────────────────────────────────
# 1. LookupAgentTool — lookup-agent
# ──────────────────────────────────────────────────────────────

class LookupAgentInput(BaseModel):
    cloud_id: str = Field(description="The Cloud ID of the agent to look up")


class LookupAgentTool(BaseTool):
    """Look up an agent's public profile."""

    name: str = "lookup_cloud_agent"
    description: str = (
        "Look up an AI agent's public profile in the Citizen of the Cloud registry. "
        "Returns name, purpose, trust score, autonomy level, capabilities, and status. "
        "Informational lookup — not cryptographic verification."
    )
    args_schema: Type[BaseModel] = LookupAgentInput
    registry_url: str = DEFAULT_REGISTRY

    def _run(self, cloud_id: str) -> str:
        agent = lookup_agent(self.registry_url, cloud_id)
        if not agent:
            return f"Agent not found or inactive: {cloud_id}"
        return _fmt_agent(agent)


# ──────────────────────────────────────────────────────────────
# 2. GetServerIdentityTool — get-server-identity (own passport)
# ──────────────────────────────────────────────────────────────

class GetServerIdentityInput(BaseModel):
    cloud_id: str = Field(description="This agent's own Cloud ID")
    private_key: str = Field(description="This agent's PEM-encoded private key")


class GetServerIdentityTool(BaseTool):
    """Fetch your own agent passport from the registry."""

    name: str = "get_server_identity"
    description: str = (
        "Fetch this agent's own passport from the registry. Use to confirm "
        "your registration is active and inspect your published profile."
    )
    args_schema: Type[BaseModel] = GetServerIdentityInput
    registry_url: str = DEFAULT_REGISTRY

    def _run(self, cloud_id: str, private_key: str) -> str:
        identity = CloudIdentity(cloud_id=cloud_id, private_key=private_key, registry_url=self.registry_url)
        passport = identity.get_passport()
        if not passport:
            return f"No passport found for {cloud_id}"
        return _fmt_agent(passport)


# ──────────────────────────────────────────────────────────────
# 3. ListDirectoryTool — list-directory
# ──────────────────────────────────────────────────────────────

class ListDirectoryInput(BaseModel):
    limit: int = Field(default=20, description="Maximum number of entries to summarize in the response")


class ListDirectoryTool(BaseTool):
    """List the public agent directory."""

    name: str = "list_cloud_directory"
    description: str = (
        "List public entries in the Citizen of the Cloud agent directory. "
        "Returns a summary of registered agents."
    )
    args_schema: Type[BaseModel] = ListDirectoryInput
    registry_url: str = DEFAULT_REGISTRY

    def _run(self, limit: int = 20) -> str:
        agents = list_directory(self.registry_url)
        if not agents:
            return "Directory is empty."
        lines = [f"{len(agents)} agent(s) in directory (showing up to {limit}):"]
        for a in agents[:limit]:
            lines.append(
                f"  - {a.get('name','?')} ({a.get('cloud_id','?')}) "
                f"trust={a.get('trust_score','?')} status={a.get('status','?')}"
            )
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# 4. GovernanceFeedTool — governance-feed
# ──────────────────────────────────────────────────────────────

class GovernanceFeedInput(BaseModel):
    limit: int = Field(default=20, description="Maximum number of events to summarize")


class GovernanceFeedTool(BaseTool):
    """Read the governance activity feed."""

    name: str = "governance_feed"
    description: str = (
        "Read the Citizen of the Cloud governance activity feed. Returns recent "
        "registry events (registrations, verifications, reports, trust adjustments)."
    )
    args_schema: Type[BaseModel] = GovernanceFeedInput
    registry_url: str = DEFAULT_REGISTRY

    def _run(self, limit: int = 20) -> str:
        feed = get_governance_feed(self.registry_url)
        if not feed:
            return "Governance feed is empty."
        lines = [f"{len(feed)} governance event(s) (showing up to {limit}):"]
        for ev in feed[:limit]:
            lines.append(
                f"  - {ev.get('event_type', ev.get('type','?'))} "
                f"at {ev.get('created_at', ev.get('timestamp','?'))}"
            )
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# 5. VerifyAgentTool — verify-agent (simple header verify)
# ──────────────────────────────────────────────────────────────

class VerifyAgentInput(BaseModel):
    cloud_id: str = Field(description="X-Cloud-ID header")
    timestamp: str = Field(description="X-Cloud-Timestamp header")
    signature: str = Field(description="X-Cloud-Signature header")


class VerifyAgentTool(BaseTool):
    """Verify another agent's identity from signed headers."""

    name: str = "verify_cloud_agent"
    description: str = (
        "Verify an AI agent's identity using the Citizen of the Cloud protocol. "
        "Requires the three X-Cloud-* headers from the incoming request."
    )
    args_schema: Type[BaseModel] = VerifyAgentInput
    registry_url: str = DEFAULT_REGISTRY

    def _run(self, cloud_id: str, timestamp: str, signature: str) -> str:
        headers = {
            "X-Cloud-ID": cloud_id,
            "X-Cloud-Timestamp": timestamp,
            "X-Cloud-Signature": signature,
        }
        result = verify_agent(headers, registry_url=self.registry_url)
        if result.get("verified"):
            return f"VERIFIED — {_fmt_agent(result['agent'])}"
        return f"NOT VERIFIED — Reason: {result.get('reason')}"


# ──────────────────────────────────────────────────────────────
# 6. VerifyRequestTool — verify-request (request-bound)
# ──────────────────────────────────────────────────────────────

class VerifyRequestInput(BaseModel):
    cloud_id: str = Field(description="X-Cloud-ID header")
    timestamp: str = Field(description="X-Cloud-Timestamp header")
    signature: str = Field(description="X-Cloud-Signature header")
    url: str = Field(description="The exact request URL the signature is bound to")
    method: str = Field(description="HTTP method (GET, POST, etc.)")
    body: str = Field(default="", description="Request body (optional)")


class VerifyRequestTool(BaseTool):
    """Verify a request-bound signature (also covers URL + method + body)."""

    name: str = "verify_cloud_request"
    description: str = (
        "Verify a request-bound Cloud Identity signature. Confirms the signature "
        "covers the URL, method, and body, not just the timestamp. Use this for "
        "stricter per-request authentication."
    )
    args_schema: Type[BaseModel] = VerifyRequestInput
    registry_url: str = DEFAULT_REGISTRY

    def _run(self, cloud_id: str, timestamp: str, signature: str, url: str, method: str, body: str = "") -> str:
        headers = {
            "X-Cloud-ID": cloud_id,
            "X-Cloud-Timestamp": timestamp,
            "X-Cloud-Signature": signature,
            "X-Cloud-Request-Bound": "true",
        }
        from citizenofthecloud import TrustPolicy
        policy = TrustPolicy(registry_url=self.registry_url)
        result = verify_request(headers, url=url, method=method, body=body, policy=policy)
        if result.get("verified"):
            return f"VERIFIED (request-bound) — {_fmt_agent(result['agent'])}"
        return f"NOT VERIFIED — Reason: {result.get('reason')}"


# ──────────────────────────────────────────────────────────────
# 7. RequestChallengeTool — request-challenge
# ──────────────────────────────────────────────────────────────

class RequestChallengeInput(BaseModel):
    cloud_id: str = Field(description="The Cloud ID requesting a challenge")


class RequestChallengeTool(BaseTool):
    """Request a fresh challenge nonce from the registry."""

    name: str = "request_cloud_challenge"
    description: str = (
        "Request a verification challenge nonce for a Cloud ID. The returned "
        "nonce must be signed and submitted back via respond_to_challenge."
    )
    args_schema: Type[BaseModel] = RequestChallengeInput
    registry_url: str = DEFAULT_REGISTRY

    def _run(self, cloud_id: str) -> str:
        ch = request_challenge(self.registry_url, cloud_id)
        return f"nonce={ch['nonce']} expires_in={ch.get('expires_in','?')}s"


# ──────────────────────────────────────────────────────────────
# 8. RespondToChallengeTool — respond-to-challenge
# ──────────────────────────────────────────────────────────────

class RespondChallengeInput(BaseModel):
    cloud_id: str = Field(description="The Cloud ID being verified")
    nonce: str = Field(description="The hex nonce from request_cloud_challenge")
    signature: str = Field(description="Base64 signature over the UTF-8 nonce bytes")


class RespondToChallengeTool(BaseTool):
    """Submit a signed challenge response."""

    name: str = "respond_to_cloud_challenge"
    description: str = (
        "Submit a signed challenge response. The registry validates the signature "
        "and returns the verified agent. Pair with request_cloud_challenge."
    )
    args_schema: Type[BaseModel] = RespondChallengeInput
    registry_url: str = DEFAULT_REGISTRY

    def _run(self, cloud_id: str, nonce: str, signature: str) -> str:
        result = submit_challenge_response(self.registry_url, cloud_id, nonce, signature)
        if result.get("verified"):
            return f"VERIFIED via challenge — {_fmt_agent(result['agent'])}"
        return f"NOT VERIFIED — Reason: {result.get('error') or result.get('reason')}"


# ──────────────────────────────────────────────────────────────
# 9. SignChallengeTool — sign-challenge (standalone nonce sign)
# ──────────────────────────────────────────────────────────────

class SignChallengeInput(BaseModel):
    nonce: str = Field(description="The hex nonce from request_cloud_challenge")
    private_key: str = Field(description="PEM-encoded Ed25519 private key")


class SignChallengeTool(BaseTool):
    """Sign a nonce with the agent's private key (no network call)."""

    name: str = "sign_cloud_challenge"
    description: str = (
        "Sign a challenge nonce locally with the agent's Ed25519 private key. "
        "Returns the base64-encoded signature. Pair with respond_to_cloud_challenge."
    )
    args_schema: Type[BaseModel] = SignChallengeInput

    def _run(self, nonce: str, private_key: str) -> str:
        import base64
        from cryptography.hazmat.primitives import serialization
        key = serialization.load_pem_private_key(private_key.encode("utf-8"), password=None)
        sig = key.sign(nonce.encode("utf-8"))
        return base64.b64encode(sig).decode("ascii")


# ──────────────────────────────────────────────────────────────
# 10. ProveIdentityTool — prove-identity (full loop)
# ──────────────────────────────────────────────────────────────

class ProveIdentityInput(BaseModel):
    cloud_id: str = Field(description="The agent's Cloud ID")
    private_key: str = Field(description="PEM-encoded Ed25519 private key")


class ProveIdentityTool(BaseTool):
    """Run the full challenge → sign → respond loop in one call."""

    name: str = "prove_cloud_identity"
    description: str = (
        "Prove this agent's identity to the registry by running the full "
        "challenge / sign / respond loop. Returns the verified passport."
    )
    args_schema: Type[BaseModel] = ProveIdentityInput
    registry_url: str = DEFAULT_REGISTRY

    def _run(self, cloud_id: str, private_key: str) -> str:
        identity = CloudIdentity(cloud_id=cloud_id, private_key=private_key, registry_url=self.registry_url)
        result = identity.prove_identity()
        if result.get("verified"):
            return f"VERIFIED — {_fmt_agent(result['agent'])}"
        return f"NOT VERIFIED — Reason: {result.get('error') or result.get('reason')}"


# ──────────────────────────────────────────────────────────────
# 11. SignHeadersTool — sign-headers (simple outbound)
# ──────────────────────────────────────────────────────────────

class SignHeadersInput(BaseModel):
    cloud_id: str = Field(description="The agent's Cloud ID")
    private_key: str = Field(description="PEM-encoded Ed25519 private key")


class SignHeadersTool(BaseTool):
    """Produce X-Cloud-* headers for an outbound request (timestamp-bound only)."""

    name: str = "sign_cloud_headers"
    description: str = (
        "Produce signed X-Cloud-* headers for an outbound request. The signature "
        "covers cloud_id + timestamp; use sign_cloud_request for stricter binding."
    )
    args_schema: Type[BaseModel] = SignHeadersInput

    def _run(self, cloud_id: str, private_key: str) -> str:
        identity = CloudIdentity(cloud_id=cloud_id, private_key=private_key)
        h = identity.sign()
        return (
            f"X-Cloud-ID: {h['X-Cloud-ID']}\n"
            f"X-Cloud-Timestamp: {h['X-Cloud-Timestamp']}\n"
            f"X-Cloud-Signature: {h['X-Cloud-Signature']}"
        )


# ──────────────────────────────────────────────────────────────
# 12. SignRequestTool — sign-request (request-bound)
# ──────────────────────────────────────────────────────────────

class SignRequestInput(BaseModel):
    cloud_id: str = Field(description="The agent's Cloud ID")
    private_key: str = Field(description="PEM-encoded Ed25519 private key")
    url: str = Field(description="Target request URL")
    method: str = Field(description="HTTP method")
    body: str = Field(default="", description="Request body (optional)")


class SignRequestTool(BaseTool):
    """Produce request-bound X-Cloud-* headers (covers URL + method + body hash)."""

    name: str = "sign_cloud_request"
    description: str = (
        "Produce request-bound X-Cloud-* headers for an outbound request. "
        "Signature covers cloud_id, timestamp, method, URL, and body hash."
    )
    args_schema: Type[BaseModel] = SignRequestInput

    def _run(self, cloud_id: str, private_key: str, url: str, method: str, body: str = "") -> str:
        identity = CloudIdentity(cloud_id=cloud_id, private_key=private_key)
        h = identity.sign_request(url, method, body)
        return (
            f"X-Cloud-ID: {h['X-Cloud-ID']}\n"
            f"X-Cloud-Timestamp: {h['X-Cloud-Timestamp']}\n"
            f"X-Cloud-Signature: {h['X-Cloud-Signature']}\n"
            f"X-Cloud-Request-Bound: true"
        )


# ──────────────────────────────────────────────────────────────
# 13. CloudFetchTool — cloud-fetch (signed HTTP wrapper)
# ──────────────────────────────────────────────────────────────

class CloudFetchInput(BaseModel):
    cloud_id: str = Field(description="The caller's Cloud ID")
    private_key: str = Field(description="PEM-encoded Ed25519 private key")
    url: str = Field(description="Target URL")
    method: str = Field(default="GET", description="HTTP method")
    body: Optional[str] = Field(default=None, description="Request body (optional)")


class CloudFetchTool(BaseTool):
    """Make a signed HTTP request to another agent or service."""

    name: str = "cloud_fetch"
    description: str = (
        "Make an HTTP request with automatic Cloud Identity signing. The "
        "signature is request-bound (covers URL, method, body hash)."
    )
    args_schema: Type[BaseModel] = CloudFetchInput

    def _run(self, cloud_id: str, private_key: str, url: str, method: str = "GET", body: Optional[str] = None) -> str:
        identity = CloudIdentity(cloud_id=cloud_id, private_key=private_key)
        resp = cloud_fetch(identity, url, method=method, body=body)
        body_str = resp.get("body")
        if isinstance(body_str, (dict, list)):
            import json
            body_str = json.dumps(body_str)
        return f"status={resp['status']}\nbody={body_str}"


# ──────────────────────────────────────────────────────────────
# 14. GenerateKeypairTool — generate-keypair
# ──────────────────────────────────────────────────────────────

class GenerateKeypairInput(BaseModel):
    pass


class GenerateKeypairTool(BaseTool):
    """Generate a fresh Ed25519 keypair locally."""

    name: str = "generate_cloud_keypair"
    description: str = (
        "Generate a fresh Ed25519 keypair locally. Returns PEM-encoded public "
        "and private keys. Use as the first step of agent registration."
    )
    args_schema: Type[BaseModel] = GenerateKeypairInput

    def _run(self) -> str:
        keys = generate_key_pair()
        return (
            f"public_key:\n{keys['public_key']}\n"
            f"private_key (STORE SECURELY):\n{keys['private_key']}"
        )


# ──────────────────────────────────────────────────────────────
# 15. RegisterAgentTool — register-agent (SDK-token auth)
# ──────────────────────────────────────────────────────────────

class RegisterAgentInput(BaseModel):
    sdk_token: str = Field(description="A cotc_sdk_* token from citizenofthecloud.com/account")
    name: str = Field(description="Human-readable name for the agent")
    declared_purpose: str = Field(description="What the agent does (<= 500 chars)")
    autonomy_level: str = Field(default="tool", description="'tool' | 'assistant' | 'agent' | 'self-directing'")
    capabilities: Optional[list] = Field(default=None, description="Optional list of capability strings")
    operational_domain: Optional[str] = Field(default=None, description="Optional domain string")


class RegisterAgentTool(BaseTool):
    """Register a new Cloud Identity agent (SDK-token auth)."""

    name: str = "register_cloud_agent"
    description: str = (
        "Register a new agent with the Citizen of the Cloud registry. Generates "
        "a keypair locally and posts the public key under your SDK token. Returns "
        "cloud_id and both keys. Use ONCE at agent setup time."
    )
    args_schema: Type[BaseModel] = RegisterAgentInput
    registry_url: str = DEFAULT_REGISTRY

    def _run(
        self,
        sdk_token: str,
        name: str,
        declared_purpose: str,
        autonomy_level: str = "tool",
        capabilities: Optional[list] = None,
        operational_domain: Optional[str] = None,
    ) -> str:
        from citizenofthecloud import RegistryError, CloudSDKError
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
        return (
            f"Registered: {result['cloud_id']}\n"
            f"name: {result['name']}\n"
            f"public_key:\n{result['public_key']}\n"
            f"private_key (STORE SECURELY):\n{result['private_key']}"
        )


# ──────────────────────────────────────────────────────────────
# 16. ReportAgentTool — report-agent (Bearer auth)
# ──────────────────────────────────────────────────────────────

class ReportAgentInput(BaseModel):
    sdk_token: str = Field(description="A cotc_sdk_* token with 'manage' scope, or a user JWT")
    cloud_id: str = Field(description="Cloud ID of the agent being reported")
    report_type: str = Field(
        description="One of: impersonation | malicious_behavior | spam | covenant_violation | inaccurate_registration"
    )
    evidence: str = Field(description="Evidence text (20–2000 chars)")


class ReportAgentTool(BaseTool):
    """File a governance report against a misbehaving agent."""

    name: str = "report_cloud_agent"
    description: str = (
        "File a governance report against another agent. Requires a Bearer "
        "token (cotc_sdk_* with 'manage' scope, or a user JWT). report_type must "
        "be one of: impersonation, malicious_behavior, spam, covenant_violation, "
        "inaccurate_registration. Evidence must be 20-2000 chars."
    )
    args_schema: Type[BaseModel] = ReportAgentInput
    registry_url: str = DEFAULT_REGISTRY

    def _run(self, sdk_token: str, cloud_id: str, report_type: str, evidence: str) -> str:
        import json
        import urllib.request
        import urllib.error
        body = json.dumps({
            "cloud_id": cloud_id,
            "report_type": report_type,
            "evidence": evidence,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.registry_url.rstrip('/')}/api/report",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {sdk_token}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return f"Report filed: id={data.get('report_id') or data.get('id') or 'ok'}"
        except urllib.error.HTTPError as e:
            try:
                err = json.loads(e.read().decode("utf-8"))
                return f"Report error ({e.code}): {err.get('error', str(e))}"
            except Exception:
                return f"Report error: HTTP {e.code}"
        except urllib.error.URLError as e:
            return f"Report error: registry unreachable: {e}"


# ──────────────────────────────────────────────────────────────
# 17. CheckTrustTool — check-trust (threshold helper)
# ──────────────────────────────────────────────────────────────

class CheckTrustInput(BaseModel):
    cloud_id: str = Field(description="The Cloud ID of the agent to check")
    minimum_trust_score: float = Field(default=0.5, description="Minimum trust score required (0.0–1.0)")


class CheckTrustTool(BaseTool):
    """Quick PASS/FAIL trust threshold check."""

    name: str = "check_agent_trust"
    description: str = (
        "Check if an AI agent meets a minimum trust score threshold. Returns "
        "PASS or FAIL with the agent's current trust score."
    )
    args_schema: Type[BaseModel] = CheckTrustInput
    registry_url: str = DEFAULT_REGISTRY

    def _run(self, cloud_id: str, minimum_trust_score: float = 0.5) -> str:
        agent = lookup_agent(self.registry_url, cloud_id)
        if not agent:
            return f"FAIL — Agent not found or inactive: {cloud_id}"
        score = agent.get("trust_score", 0) or 0
        name = agent.get("name", "Unknown")
        if score >= minimum_trust_score:
            return f"PASS — {name} trust={score} (threshold={minimum_trust_score})"
        return f"FAIL — {name} trust={score} (below threshold={minimum_trust_score})"


# ──────────────────────────────────────────────────────────────
# Convenience — all 17 agent-callable tools
# ──────────────────────────────────────────────────────────────

def cloud_identity_tools(registry_url: str = DEFAULT_REGISTRY) -> List[BaseTool]:
    """Return all 17 agent-callable LangChain tools in one list."""
    return [
        LookupAgentTool(registry_url=registry_url),
        GetServerIdentityTool(registry_url=registry_url),
        ListDirectoryTool(registry_url=registry_url),
        GovernanceFeedTool(registry_url=registry_url),
        VerifyAgentTool(registry_url=registry_url),
        VerifyRequestTool(registry_url=registry_url),
        RequestChallengeTool(registry_url=registry_url),
        RespondToChallengeTool(registry_url=registry_url),
        SignChallengeTool(),
        ProveIdentityTool(registry_url=registry_url),
        SignHeadersTool(),
        SignRequestTool(),
        CloudFetchTool(),
        GenerateKeypairTool(),
        RegisterAgentTool(registry_url=registry_url),
        ReportAgentTool(registry_url=registry_url),
        CheckTrustTool(registry_url=registry_url),
    ]
