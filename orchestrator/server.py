"""
Uvicorn entry point for the DCS orchestrator REST API.
"""

from __future__ import annotations

import uvicorn

from .api.app import create_app
from .config import OrchestratorConfig


def serve(config: OrchestratorConfig) -> None:
    """Start the orchestrator HTTP server using uvicorn."""
    uvicorn.run(
        create_app(config),
        host=config.host,
        port=config.port,
        log_level=config.log_level,
    )
