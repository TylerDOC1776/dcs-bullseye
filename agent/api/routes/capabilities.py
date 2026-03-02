"""
GET /agent/v1/capabilities — agent capability advertisement.
"""

from __future__ import annotations

import platform
import sys

from fastapi import APIRouter, Request

from ..models import AgentCapabilities

router = APIRouter()

_SUPPORTED_ACTIONS = ["start", "stop", "restart", "logs_bundle", "mission_load"]


@router.get("/capabilities", response_model=AgentCapabilities)
async def get_capabilities(request: Request) -> AgentCapabilities:
    return AgentCapabilities(
        os=platform.system(),
        osVersion=platform.version(),
        hostname=platform.node(),
        pythonVersion=sys.version,
        supportedActions=_SUPPORTED_ACTIONS,
        notes="update is not yet implemented",
    )
