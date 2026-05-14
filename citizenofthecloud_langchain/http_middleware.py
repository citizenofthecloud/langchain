"""
FastAPI route-guard middleware for serving LangChain endpoints behind
Cloud Identity verification.

This is the framework's structural http-middleware: a FastAPI/Starlette
BaseHTTPMiddleware that verifies the inbound X-Cloud-* headers on every
request and rejects unverified callers before they reach a LangChain
chain/agent endpoint.

Re-exports the upstream `citizenofthecloud.fastapi.CloudGuard` middleware
with a LangChain-flavored alias and a route-decorator helper.
"""

from typing import Optional

try:
    from citizenofthecloud.fastapi import CloudGuard as _CloudGuard
    from citizenofthecloud.fastapi import cloud_guard_decorator as _decorator
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "FastAPI extras required. Install with: "
        "pip install 'citizenofthecloud[fastapi]'"
    ) from e

from citizenofthecloud import TrustPolicy


class CloudIdentityRouteGuard(_CloudGuard):
    """
    FastAPI route-guard middleware for LangChain endpoints.

    Add to a FastAPI app that exposes a LangServe / LangChain chain to
    automatically reject inbound requests without valid Cloud Identity
    headers before they hit the chain.

    Usage:
        from fastapi import FastAPI
        from citizenofthecloud_langchain import CloudIdentityRouteGuard
        from citizenofthecloud import TrustPolicy

        app = FastAPI()
        app.add_middleware(
            CloudIdentityRouteGuard,
            policy=TrustPolicy(minimum_trust_score=0.5),
            registry_url="https://citizenofthecloud.com",
        )
    """
    pass


def cloud_guard_route(policy: Optional[TrustPolicy] = None, **kwargs):
    """
    Decorator form for FastAPI routes that serve LangChain chains.

    Usage:
        from fastapi import FastAPI, Request
        from citizenofthecloud_langchain import cloud_guard_route

        app = FastAPI()

        @app.post("/chain")
        @cloud_guard_route(minimum_trust_score=0.5)
        async def run_chain(request: Request):
            return await chain.ainvoke(await request.json())
    """
    return _decorator(policy=policy, **kwargs)
