"""
Uvicorn entry point for the DCS agent REST API.
"""

from __future__ import annotations

import uvicorn

from .api.app import create_app
from .config import AgentConfig


def serve(config: AgentConfig) -> None:
    """Start the agent HTTP server using uvicorn."""
    uvicorn.run(create_app(config), host=config.host, port=config.port)
