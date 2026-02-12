"""
Citizen of the Cloud — LangChain Integration

Adds cryptographic identity and trust verification to LangChain agents.
Wraps the citizenofthecloud Python SDK into LangChain-compatible tools
and middleware.

Tools:
    VerifyAgentTool     — Verify another agent's identity and trust score
    LookupAgentTool     — Look up an agent's profile by Cloud ID
    CheckTrustTool      — Quick trust score check with pass/fail threshold

Middleware:
    CloudIdentityMiddleware — Auto-sign all outbound requests
    cloud_guard_chain       — Verify incoming requests before chain execution

Usage:
    from citizenofthecloud_langchain import (
        VerifyAgentTool,
        LookupAgentTool,
        CheckTrustTool,
        CloudIdentityMiddleware,
        cloud_guard_chain,
    )
"""

from citizenofthecloud_langchain.tools import (
    VerifyAgentTool,
    LookupAgentTool,
    CheckTrustTool,
)
from citizenofthecloud_langchain.middleware import (
    CloudIdentityMiddleware,
    cloud_guard_chain,
)
from citizenofthecloud_langchain.http import CloudIdentityHTTPClient

__all__ = [
    "VerifyAgentTool",
    "LookupAgentTool",
    "CheckTrustTool",
    "CloudIdentityMiddleware",
    "cloud_guard_chain",
    "CloudIdentityHTTPClient",
]

__version__ = "0.1.0"
