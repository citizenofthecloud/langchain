"""
LangChain middleware for Citizen of the Cloud identity.

Provides two integration patterns:

1. CloudIdentityMiddleware — Wraps a LangChain agent to auto-sign
   outbound requests and verify inbound requests.

2. cloud_guard_chain — A pre-chain verification step that rejects
   requests from unverified or untrusted agents before the main
   chain executes.
"""

import os
from typing import Optional, Dict, Any, Callable
from citizenofthecloud import CloudIdentity, verify_agent


class CloudIdentityMiddleware:
    """
    Middleware that adds Cloud Identity to a LangChain agent.

    Handles two concerns:
    - Outbound: Signs all HTTP requests made by the agent
    - Inbound: Verifies incoming requests before processing

    Usage:
        from citizenofthecloud_langchain import CloudIdentityMiddleware

        middleware = CloudIdentityMiddleware.from_env()

        # Verify an incoming request before processing
        result = middleware.verify_inbound(request_headers)
        if not result["verified"]:
            return {"error": result["reason"]}

        # Sign outbound headers for requests to other agents
        signed_headers = middleware.sign_outbound()
    """

    def __init__(
        self,
        cloud_id: str,
        private_key: str,
        trust_policy: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize middleware.

        Args:
            cloud_id: This agent's Cloud ID
            private_key: This agent's private key (PEM format)
            trust_policy: Optional verification policy with keys:
                - max_age: Max signature age in seconds (default 300)
                - require_covenant: Require covenant signed (default True)
                - minimum_trust_score: Min trust score (default 0.0)
                - allowed_autonomy_levels: List of allowed levels (default all)
                - blocked_agents: List of blocked Cloud IDs (default none)
        """
        self.identity = CloudIdentity(
            cloud_id=cloud_id,
            private_key=private_key,
        )
        self.trust_policy = trust_policy or {}

    @classmethod
    def from_env(
        cls,
        cloud_id_var: str = "CLOUD_ID",
        private_key_var: str = "CLOUD_PRIVATE_KEY",
        trust_policy: Optional[Dict[str, Any]] = None,
    ) -> "CloudIdentityMiddleware":
        """Create middleware from environment variables."""
        cloud_id = os.environ.get(cloud_id_var)
        private_key = os.environ.get(private_key_var)

        if not cloud_id or not private_key:
            raise ValueError(
                f"Missing environment variables: {cloud_id_var} and/or "
                f"{private_key_var}"
            )

        return cls(
            cloud_id=cloud_id,
            private_key=private_key,
            trust_policy=trust_policy,
        )

    def sign_outbound(self) -> Dict[str, str]:
        """
        Generate signed headers for an outbound request.

        Returns:
            Dict with X-Cloud-ID, X-Cloud-Timestamp, X-Cloud-Signature
        """
        return self.identity.sign()

    def sign_outbound_request(self, url: str, method: str, body: Optional[str] = None) -> Dict[str, str]:
        """
        Generate request-bound signed headers (includes URL, method, body hash).

        Args:
            url: The target URL
            method: HTTP method (GET, POST, etc.)
            body: Request body string (optional)

        Returns:
            Dict with X-Cloud-* headers including request-bound signature
        """
        return self.identity.sign_request(url, method, body)

    def verify_inbound(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Verify an incoming request's Cloud Identity headers.

        Args:
            headers: Request headers dict containing X-Cloud-* headers

        Returns:
            Dict with 'verified' (bool), 'agent' (dict if verified),
            'reason' (str if not verified)
        """
        return verify_agent(headers, policy=self.trust_policy)


def cloud_guard_chain(
    headers: Dict[str, str],
    minimum_trust_score: float = 0.0,
    require_covenant: bool = True,
    allowed_autonomy_levels: Optional[list] = None,
    blocked_agents: Optional[list] = None,
    on_reject: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    Pre-chain verification gate.

    Call this before executing a LangChain chain to verify the
    requesting agent. If verification fails, returns the rejection
    reason. If it passes, returns the verified agent data.

    Usage:
        from citizenofthecloud_langchain import cloud_guard_chain

        # In your endpoint handler:
        guard_result = cloud_guard_chain(
            headers=request.headers,
            minimum_trust_score=0.5,
        )

        if not guard_result["verified"]:
            return {"error": guard_result["reason"]}, 401

        # Agent is verified — run the chain
        agent_info = guard_result["agent"]
        result = my_chain.invoke({"input": query, "agent": agent_info})

    Args:
        headers: Incoming request headers
        minimum_trust_score: Minimum trust score to allow (default 0.0)
        require_covenant: Whether to require covenant signed (default True)
        allowed_autonomy_levels: Restrict to specific autonomy levels
        blocked_agents: List of Cloud IDs to block
        on_reject: Optional callback called with rejection reason

    Returns:
        Dict with 'verified', 'agent' (if verified), 'reason' (if rejected)
    """
    policy = {}

    if minimum_trust_score > 0:
        policy["minimum_trust_score"] = minimum_trust_score
    if require_covenant:
        policy["require_covenant"] = require_covenant
    if allowed_autonomy_levels:
        policy["allowed_autonomy_levels"] = allowed_autonomy_levels
    if blocked_agents:
        policy["blocked_agents"] = blocked_agents

    try:
        result = verify_agent(headers, policy=policy if policy else None)
    except Exception as e:
        result = {"verified": False, "reason": f"verification_error: {str(e)}"}

    if not result["verified"] and on_reject:
        on_reject(result["reason"])

    return result
