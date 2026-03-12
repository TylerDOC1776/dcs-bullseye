"""
Analytics reporter for the DCS Agent.

Runs as a background task: reads DCS instance status every POLL_INTERVAL seconds,
diffs player lists and mission state between polls, and POSTs join/leave/mission
events to the orchestrator's analytics endpoint.

Requires orchestrator_url and host_id set in agent config (written by installer).
If either is missing, the reporter silently skips — backwards compatible with
manually-configured installs that predate analytics.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import aiohttp

from .config import AgentConfig
from .controller import DcsController

logger = logging.getLogger(__name__)

POLL_INTERVAL = 60.0  # seconds between status checks


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class _InstanceState:
    players: set[str] = field(default_factory=set)
    mission_name: str = ""


async def _post_events(
    session: aiohttp.ClientSession,
    orchestrator_url: str,
    host_id: str,
    agent_api_key: str,
    events: list[dict],
) -> None:
    url = orchestrator_url.rstrip("/") + "/api/v1/analytics/events"
    try:
        async with session.post(
            url,
            json={"events": events},
            headers={"X-Host-Id": host_id, "X-Agent-Key": agent_api_key},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status not in (200, 204):
                text = await resp.text()
                logger.warning(
                    "[analytics] POST failed %s: %s", resp.status, text[:200]
                )
    except Exception as exc:
        logger.debug("[analytics] POST error: %s", exc)


async def run_reporter(config: AgentConfig, ctrl: DcsController) -> None:
    """Main analytics reporter loop. Runs until cancelled."""
    if not config.orchestrator_url or not config.host_id:
        logger.info(
            "[analytics] orchestrator_url or host_id not set — reporter disabled"
        )
        return

    logger.info(
        "[analytics] reporter started — host_id=%s, orchestrator=%s, interval=%ds",
        config.host_id,
        config.orchestrator_url,
        int(POLL_INTERVAL),
    )

    state: dict[str, _InstanceState] = {
        inst.service_name: _InstanceState() for inst in config.instances
    }
    loop = asyncio.get_running_loop()

    async with aiohttp.ClientSession() as session:
        while True:
            await asyncio.sleep(POLL_INTERVAL)
            events: list[dict] = []

            for inst in config.instances:
                try:
                    info = await loop.run_in_executor(None, ctrl.runtime_info, inst)
                except Exception as exc:
                    logger.debug(
                        "[analytics] runtime_info failed for %s: %s",
                        inst.service_name,
                        exc,
                    )
                    continue

                prev = state[inst.service_name]
                current_players: set[str] = set(info.get("players") or [])
                current_mission: str = info.get("mission_name") or ""
                current_map: str = info.get("map") or ""

                # Player joins
                for name in current_players - prev.players:
                    events.append(
                        {
                            "instance_id": inst.service_name,
                            "event_type": "player_join",
                            "player_name": name,
                            "mission_name": current_mission,
                            "map": current_map,
                            "timestamp": _now_iso(),
                        }
                    )

                # Player leaves
                for name in prev.players - current_players:
                    events.append(
                        {
                            "instance_id": inst.service_name,
                            "event_type": "player_leave",
                            "player_name": name,
                            "mission_name": prev.mission_name,
                            "map": current_map,
                            "timestamp": _now_iso(),
                        }
                    )

                # Mission change
                if current_mission and current_mission != prev.mission_name:
                    events.append(
                        {
                            "instance_id": inst.service_name,
                            "event_type": "mission_start",
                            "mission_name": current_mission,
                            "map": current_map,
                            "timestamp": _now_iso(),
                        }
                    )

                state[inst.service_name] = _InstanceState(
                    players=current_players,
                    mission_name=current_mission,
                )

            if events:
                logger.debug("[analytics] posting %d event(s)", len(events))
                await _post_events(
                    session,
                    config.orchestrator_url,
                    config.host_id,
                    config.api_key,
                    events,
                )
