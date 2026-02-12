"""
Signed HTTP client for LangChain agents.

Wraps the requests library to automatically sign all outbound HTTP
requests with the Citizen of the Cloud identity protocol. Use this
as a drop-in replacement when your LangChain agent makes API calls
to other agents or services.
"""

import os
import requests
from typing import Optional, Any
from citizenofthecloud import CloudIdentity


class CloudIdentityHTTPClient:
    """
    HTTP client that automatically signs requests with Cloud Identity headers.

    Usage:
        client = CloudIdentityHTTPClient(
            cloud_id="cc-...",
            private_key="-----BEGIN PRIVATE KEY-----\\n...",
        )

        # All requests are automatically signed
        response = client.get("https://other-agent.com/api/data")
        response = client.post("https://other-agent.com/api/task", json={"task": "analyze"})

    Or initialize from environment variables:
        client = CloudIdentityHTTPClient.from_env()
    """

    def __init__(self, cloud_id: str, private_key: str):
        self.identity = CloudIdentity(
            cloud_id=cloud_id,
            private_key=private_key,
        )
        self.session = requests.Session()

    @classmethod
    def from_env(
        cls,
        cloud_id_var: str = "CLOUD_ID",
        private_key_var: str = "CLOUD_PRIVATE_KEY",
    ) -> "CloudIdentityHTTPClient":
        """Create client from environment variables."""
        cloud_id = os.environ.get(cloud_id_var)
        private_key = os.environ.get(private_key_var)

        if not cloud_id or not private_key:
            raise ValueError(
                f"Missing environment variables: {cloud_id_var} and/or "
                f"{private_key_var}. Set these to your agent's Cloud ID "
                f"and private key."
            )

        return cls(cloud_id=cloud_id, private_key=private_key)

    def _signed_headers(self, extra_headers: Optional[dict] = None) -> dict:
        """Generate signed headers, merged with any extra headers."""
        headers = self.identity.sign()
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def get(self, url: str, headers: Optional[dict] = None, **kwargs: Any) -> requests.Response:
        """Signed GET request."""
        return self.session.get(url, headers=self._signed_headers(headers), **kwargs)

    def post(self, url: str, headers: Optional[dict] = None, **kwargs: Any) -> requests.Response:
        """Signed POST request."""
        return self.session.post(url, headers=self._signed_headers(headers), **kwargs)

    def put(self, url: str, headers: Optional[dict] = None, **kwargs: Any) -> requests.Response:
        """Signed PUT request."""
        return self.session.put(url, headers=self._signed_headers(headers), **kwargs)

    def delete(self, url: str, headers: Optional[dict] = None, **kwargs: Any) -> requests.Response:
        """Signed DELETE request."""
        return self.session.delete(url, headers=self._signed_headers(headers), **kwargs)

    def request(self, method: str, url: str, headers: Optional[dict] = None, **kwargs: Any) -> requests.Response:
        """Signed request with arbitrary method."""
        return self.session.request(method, url, headers=self._signed_headers(headers), **kwargs)
