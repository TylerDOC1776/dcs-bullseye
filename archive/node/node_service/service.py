"""
Windows service wrapper for the node agent.

Allows running the Python controller as a background service instead of the
legacy restart executable.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from typing import Optional

from .comm import CommandTransport, HttpCommandClient, LocalCommandTransport
from .config import ConfigError, NodeConfig, load_config
from .controller import DcsController

LOG = logging.getLogger("node_service.service")

try:
    import win32event
    import win32service
    import win32serviceutil
except Exception:  # pragma: no cover - allows development on non-Windows hosts
    win32event = win32service = win32serviceutil = None  # type: ignore[assignment]


class NodeServiceApp:
    """Async runner used by the Windows service and CLI."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.stop_event = asyncio.Event()
        self.config: Optional[NodeConfig] = None
        self.controller: Optional[DcsController] = None
        self.command_transport: Optional[CommandTransport] = None
        self.http_client: Optional[HttpCommandClient] = None
        self.heartbeat_interval = 30
        self.command_poll_interval = 5
        self.agent_version = "dev"

    def reload_config(self) -> None:
        cfg = load_config(self.config_path) if self.config_path else load_config()
        self.config = cfg
        self.controller = DcsController(cfg)
        if cfg.command_transport == "http":
            http_client = HttpCommandClient(cfg.vps_endpoint, cfg.api_key, cfg.node_id)
            self.command_transport = http_client
            self.http_client = http_client
        else:
            self.command_transport = LocalCommandTransport(cfg.command_queue_dir)
            self.http_client = None
        self.heartbeat_interval = cfg.heartbeat_interval
        self.command_poll_interval = cfg.command_poll_interval
        LOG.info(
            "Loaded config for %s instance(s); transport=%s; command dir=%s",
            len(self.controller.instances),
            cfg.command_transport,
            cfg.command_queue_dir,
        )

    async def run(self) -> None:
        self.reload_config()
        signal.signal(signal.SIGTERM, lambda *_: asyncio.create_task(self.shutdown()))
        signal.signal(signal.SIGINT, lambda *_: asyncio.create_task(self.shutdown()))
        await asyncio.gather(
            self._heartbeat_loop(),
            self._command_loop(),
            self.stop_event.wait(),
        )

    async def shutdown(self) -> None:
        LOG.info("Shutting down node service...")
        self.stop_event.set()

    async def _heartbeat_loop(self) -> None:
        """Periodically log heartbeat and push telemetry to the hub when available."""
        interval = max(5, self.heartbeat_interval)
        controller = self.controller
        cfg = self.config
        while not self.stop_event.is_set():
            count = len(controller.instances) if controller else 0
            node_label = cfg.node_id if cfg else "unknown"
            payload = {
                "status": "online" if controller else "error",
                "message": None if controller else "Controller not initialized",
                "instances": controller.instance_statuses() if controller else [],
                "version": self.agent_version,
            }
            LOG.info("Heartbeat [%s]: %s instances ready", node_label, count)
            if self.http_client:
                try:
                    await self.http_client.send_heartbeat(payload)
                except Exception as exc:  # noqa: BLE001
                    LOG.warning("Failed to send heartbeat to hub: %s", exc)
            await asyncio.sleep(interval)

    async def _command_loop(self) -> None:
        """Poll the local command queue and execute actions."""
        interval = max(1, self.command_poll_interval)
        transport = self.command_transport
        controller = self.controller
        if not transport or not controller:
            LOG.warning("Command loop missing transport/controller; skipping.")
            return

        while not self.stop_event.is_set():
            try:
                envelopes = await transport.fetch_commands()
            except Exception as exc:  # noqa: BLE001
                LOG.error("Failed to fetch commands: %s", exc)
                await asyncio.sleep(interval)
                continue

            for envelope in envelopes:
                success, message = await self._execute_command(controller, envelope.command)
                try:
                    await transport.acknowledge(envelope, success, message=message)
                except Exception as exc:  # noqa: BLE001
                    LOG.error("Failed to acknowledge command %s: %s", envelope.command.id, exc)
            await asyncio.sleep(interval)

    async def _execute_command(self, controller: DcsController, command) -> tuple[bool, Optional[str]]:
        LOG.info("Executing command %s -> %s %s", command.id, command.action, command.instance)
        message = None
        try:
            action = command.action.lower()
            if action == "start":
                controller.start_instance(command.instance)
            elif action == "stop":
                controller.stop_instance(command.instance)
            elif action == "restart":
                controller.restart_instance(command.instance)
            elif action == "deploy_mission":
                if not command.params:
                    raise ValueError("deploy_mission requires params")
                target = controller.deploy_mission(command.instance, command.params)
                message = f"Mission stored at {target}"
            elif action == "collect_logs":
                lines = None
                if command.params and "lines" in command.params:
                    lines = int(command.params["lines"])
                bundle = controller.collect_logs(command.instance, lines=lines)
                if self.http_client:
                    try:
                        log_record = await self.http_client.upload_log_bundle(
                            bundle,
                            command.instance,
                            command.id,
                        )
                        message = f"Log bundle uploaded (id={log_record.get('id')})"
                    except Exception as exc:  # noqa: BLE001
                        LOG.warning("Failed to upload log bundle: %s", exc)
                        message = f"Log bundle saved to {bundle}"
                else:
                    message = f"Log bundle saved to {bundle}"
            else:
                raise ValueError(f"Unsupported action '{command.action}'")
            return True, message
        except Exception as exc:  # noqa: BLE001
            LOG.error("Command %s failed: %s", command.id, exc)
            return False, str(exc)


if win32serviceutil:

    class NodeWindowsService(win32serviceutil.ServiceFramework):
        _svc_name_ = "DCSNodeService"
        _svc_display_name_ = "DCS Admin Node Service"
        _svc_description_ = "Controls DCS instances and communicates with the central bot."

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
            self.loop = asyncio.new_event_loop()
            self.app = NodeServiceApp()

        def SvcDoRun(self):
            asyncio.set_event_loop(self.loop)
            try:
                self.loop.run_until_complete(self.app.run())
            except ConfigError as err:
                LOG.error("Service halted: %s", err)
            finally:
                self.loop.close()

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self.loop.call_soon_threadsafe(lambda: asyncio.create_task(self.app.shutdown()))
            win32event.SetEvent(self.hWaitStop)


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    if win32serviceutil:
        win32serviceutil.HandleCommandLine(NodeWindowsService)
    else:
        # Fallback for development/testing: run the async loop directly.
        asyncio.run(NodeServiceApp().run())


if __name__ == "__main__":
    main()
