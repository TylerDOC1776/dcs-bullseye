"""
Discord bot that enqueues commands on the hub API.

Usage:
    export DISCORD_BOT_TOKEN=...
    export HUB_BASE_URL=https://hub.example.com
    export HUB_ADMIN_TOKEN=...
    python -m hub.bot
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
from typing import Optional

import discord
from discord.ext import commands

from .bot_config import BotConfig, load_bot_config
from .hub_client import HubAdminClient

LOG = logging.getLogger("hub.bot")


def create_bot(config: BotConfig, hub_client: HubAdminClient) -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

    async def ensure_channel(ctx: commands.Context) -> bool:
        if config.command_channel_id and ctx.channel.id != config.command_channel_id:
            return False
        return True

    def resolve_node(node: Optional[str]) -> str:
        if node:
            return node
        if config.default_node:
            return config.default_node
        raise commands.BadArgument("Node ID is required.")

    async def enqueue(
        ctx: commands.Context, node: str, instance: str, action: str, params: Optional[dict] = None
    ) -> tuple[dict, str]:
        node_id = resolve_node(node)
        record = await hub_client.enqueue_command(node_id, action, instance, params)
        await ctx.send(
            f"Queued `{action}` for `{node_id}/{instance}` | Command ID `{record['id']}` | status: `{record['status']}`"
        )
        return record, node_id

    async def wait_and_send_log(ctx: commands.Context, command_id: str, node_id: str, instance: str):
        timeout = 90
        message_sent = False
        try:
            log_record = await hub_client.wait_for_log(command_id, timeout=timeout, poll_interval=3.0)
            if not log_record:
                await ctx.send(
                    f"⏳ Log bundle for `{node_id}/{instance}` not ready after {timeout}s. "
                    "Use `!logfiles` to check later."
                )
                return
            filename, content = await hub_client.download_log(log_record["id"])
            attachment = discord.File(io.BytesIO(content), filename=filename)
            await ctx.send(
                f"📄 Log bundle ready for `{node_id}/{log_record['instance']}` (cmd `{command_id[:8]}`)",
                file=attachment,
            )
            message_sent = True
        except Exception as exc:  # noqa: BLE001
            LOG.error("Failed to fetch log bundle for %s/%s: %s", node_id, instance, exc)
            await ctx.send(f"⚠️ Failed to fetch log bundle for `{node_id}/{instance}`: {exc}")
        finally:
            if not message_sent:
                LOG.info("Log attachment task completed for %s/%s (command %s)", node_id, instance, command_id)

    @bot.event
    async def on_ready():
        LOG.info("Bot ready as %s", bot.user)
        if config.command_channel_id:
            channel = bot.get_channel(config.command_channel_id)
            if channel:
                await channel.send("✅ Hub bot online.")

    @bot.command()
    async def start(ctx: commands.Context, node: str, instance: str):
        if not await ensure_channel(ctx):
            return
        await enqueue(ctx, node, instance, "start")

    @bot.command()
    async def stop(ctx: commands.Context, node: str, instance: str):
        if not await ensure_channel(ctx):
            return
        await enqueue(ctx, node, instance, "stop")

    @bot.command()
    async def restart(ctx: commands.Context, node: str, instance: str):
        if not await ensure_channel(ctx):
            return
        await enqueue(ctx, node, instance, "restart")

    @bot.command(name="deploy")
    async def deploy_mission(ctx: commands.Context, node: str, instance: str):
        if not await ensure_channel(ctx):
            return
        if not ctx.message.attachments:
            await ctx.send("Attach a `.miz` file with the command.")
            return
        attachment = ctx.message.attachments[0]
        data = await attachment.read()
        params = {
            "filename": attachment.filename,
            "content_b64": base64.b64encode(data).decode("ascii"),
        }
        await enqueue(ctx, node, instance, "deploy_mission", params=params)

    @bot.command(name="logs")
    async def collect_logs(ctx: commands.Context, node: str, instance: str, lines: Optional[int] = None):
        if not await ensure_channel(ctx):
            return
        params = {"lines": lines} if lines else None
        record, node_id = await enqueue(ctx, node, instance, "collect_logs", params=params)
        bot.loop.create_task(wait_and_send_log(ctx, record["id"], node_id, instance))

    @bot.command(name="logfiles")
    async def list_logs(ctx: commands.Context, node: Optional[str] = None):
        if not await ensure_channel(ctx):
            return
        node_id = resolve_node(node) if node else None
        records = await hub_client.list_logs(node_id=node_id)
        if not records:
            await ctx.send("No log bundles available.")
            return
        lines = []
        for record in sorted(records, key=lambda r: r["created_at"], reverse=True)[:10]:
            lines.append(
                f"`{record['id'][:8]}` node={record['node_id']} instance={record['instance']} "
                f"size={record['size']} created={record['created_at']}"
            )
        await ctx.send("\n".join(lines))

    @bot.command(name="logfile")
    async def download_log(ctx: commands.Context, log_id: str):
        if not await ensure_channel(ctx):
            return
        try:
            filename, content = await hub_client.download_log(log_id)
        except Exception as exc:  # noqa: BLE001
            await ctx.send(f"Failed to download log `{log_id}`: {exc}")
            return
        attachment = discord.File(io.BytesIO(content), filename=filename)
        await ctx.send(file=attachment)

    @bot.command(name="commands")
    async def list_commands(ctx: commands.Context, node: Optional[str] = None):
        if not await ensure_channel(ctx):
            return
        node_id = resolve_node(node)
        records = await hub_client.list_commands(node_id)
        if not records:
            await ctx.send(f"No commands found for `{node_id}`.")
            return
        lines = []
        for record in sorted(records, key=lambda x: x["created_at"], reverse=True)[:10]:
            lines.append(
                f"`{record['id'][:8]}` {record['action']} {record['instance']} "
                f"status={record['status']} created={record['created_at']}"
            )
        await ctx.send("\n".join(lines))

    @bot.command(name="help")
    async def show_help(ctx: commands.Context):
        if not await ensure_channel(ctx):
            return
        await ctx.send(
            "Commands:\n"
            "`!start <node> <instance>`\n"
            "`!stop <node> <instance>`\n"
            "`!restart <node> <instance>`\n"
            "`!deploy <node> <instance>` (attach .miz)\n"
            "`!logs <node> <instance> [lines]`\n"
            "`!logfiles [node]`\n"
            "`!logfile <log_id>`\n"
            "`!commands [node]`"
        )

    return bot


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    config = load_bot_config()
    hub_client = HubAdminClient(config.hub_url, config.hub_token)
    bot = create_bot(config, hub_client)
    try:
        await bot.start(config.discord_token)
    finally:
        await hub_client.close()


if __name__ == "__main__":
    asyncio.run(main())
