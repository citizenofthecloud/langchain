"""
Observability callbacks for LangChain.

CloudIdentityCallbackHandler hooks into LangChain's BaseCallbackHandler
contract to log Cloud Identity tool invocations as a chain executes. Use
it to get structured observability over which identity tools an agent
called and what those calls returned.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:  # pragma: no cover
    BaseCallbackHandler = object  # type: ignore[misc,assignment]

logger = logging.getLogger("citizenofthecloud.langchain")

_IDENTITY_TOOL_NAMES = {
    "lookup_cloud_agent",
    "get_server_identity",
    "list_cloud_directory",
    "governance_feed",
    "verify_cloud_agent",
    "verify_cloud_request",
    "request_cloud_challenge",
    "respond_to_cloud_challenge",
    "sign_cloud_challenge",
    "prove_cloud_identity",
    "sign_cloud_headers",
    "sign_cloud_request",
    "cloud_fetch",
    "generate_cloud_keypair",
    "register_cloud_agent",
    "report_cloud_agent",
    "check_agent_trust",
}


class CloudIdentityCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler that logs Cloud Identity tool activity.

    Usage:
        from langchain.agents import AgentExecutor
        from citizenofthecloud_langchain import CloudIdentityCallbackHandler

        handler = CloudIdentityCallbackHandler()
        executor = AgentExecutor(agent=..., tools=..., callbacks=[handler])
    """

    def __init__(self, log_all_tools: bool = False, on_event: Optional[callable] = None) -> None:
        self._log_all = log_all_tools
        self._on_event = on_event
        self.events: List[Dict[str, Any]] = []

    def _emit(self, event: Dict[str, Any]) -> None:
        self.events.append(event)
        if self._on_event:
            try:
                self._on_event(event)
            except Exception:
                pass

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        name = serialized.get("name") if isinstance(serialized, dict) else None
        if not name or (name not in _IDENTITY_TOOL_NAMES and not self._log_all):
            return
        event = {"type": "tool_start", "tool": name, "run_id": str(run_id)}
        logger.info("cloud_identity_tool_start: %s", name)
        self._emit(event)

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        out = str(output) if output is not None else ""
        if not out:
            return
        verdict = None
        if "VERIFIED" in out and "NOT VERIFIED" not in out:
            verdict = "verified"
        elif "NOT VERIFIED" in out:
            verdict = "rejected"
        elif out.startswith("PASS"):
            verdict = "pass"
        elif out.startswith("FAIL"):
            verdict = "fail"
        event = {"type": "tool_end", "run_id": str(run_id), "verdict": verdict, "sample": out[:120]}
        if verdict:
            logger.info("cloud_identity_tool_end: verdict=%s", verdict)
        self._emit(event)

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        event = {"type": "tool_error", "run_id": str(run_id), "error": str(error)}
        logger.warning("cloud_identity_tool_error: %s", error)
        self._emit(event)
