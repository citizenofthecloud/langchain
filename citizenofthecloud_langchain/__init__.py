"""
Citizen of the Cloud — LangChain Integration

Cryptographic identity and trust verification for LangChain agents.

Tool surface — 20 items (17 agent-callable + 3 structural primitives):

Agent-callable BaseTool subclasses (17):
    LookupAgentTool, GetServerIdentityTool, ListDirectoryTool,
    GovernanceFeedTool, VerifyAgentTool, VerifyRequestTool,
    RequestChallengeTool, RespondToChallengeTool, SignChallengeTool,
    ProveIdentityTool, SignHeadersTool, SignRequestTool, CloudFetchTool,
    GenerateKeypairTool, RegisterAgentTool, ReportAgentTool, CheckTrustTool

Structural primitives (3):
    18. CloudIdentityRouteGuard / cloud_guard_route — FastAPI route-guard middleware
    19. cloud_guard_chain — pre-chain verification gate (framework-native)
    20. CloudIdentityCallbackHandler — LangChain observability callbacks
"""

from citizenofthecloud_langchain.tools import (
    # Agent-callable tools (17)
    LookupAgentTool,
    GetServerIdentityTool,
    ListDirectoryTool,
    GovernanceFeedTool,
    VerifyAgentTool,
    VerifyRequestTool,
    RequestChallengeTool,
    RespondToChallengeTool,
    SignChallengeTool,
    ProveIdentityTool,
    SignHeadersTool,
    SignRequestTool,
    CloudFetchTool,
    GenerateKeypairTool,
    RegisterAgentTool,
    ReportAgentTool,
    CheckTrustTool,
    # convenience
    cloud_identity_tools,
)
from citizenofthecloud_langchain.middleware import (
    CloudIdentityMiddleware,
    cloud_guard_chain,
)
from citizenofthecloud_langchain.http import CloudIdentityHTTPClient
from citizenofthecloud_langchain.http_middleware import (
    CloudIdentityRouteGuard,
    cloud_guard_route,
)
from citizenofthecloud_langchain.callbacks import CloudIdentityCallbackHandler

__all__ = [
    # Agent-callable tools (17)
    "LookupAgentTool",
    "GetServerIdentityTool",
    "ListDirectoryTool",
    "GovernanceFeedTool",
    "VerifyAgentTool",
    "VerifyRequestTool",
    "RequestChallengeTool",
    "RespondToChallengeTool",
    "SignChallengeTool",
    "ProveIdentityTool",
    "SignHeadersTool",
    "SignRequestTool",
    "CloudFetchTool",
    "GenerateKeypairTool",
    "RegisterAgentTool",
    "ReportAgentTool",
    "CheckTrustTool",
    # Structural primitives (3)
    "CloudIdentityRouteGuard",      # 18 — http-middleware
    "cloud_guard_route",            # 18 — http-middleware (decorator form)
    "cloud_guard_chain",            # 19 — framework-native gate
    "CloudIdentityCallbackHandler", # 20 — observability callbacks
    # Helpers / legacy
    "cloud_identity_tools",
    "CloudIdentityMiddleware",
    "CloudIdentityHTTPClient",
]

__version__ = "0.2.0"
