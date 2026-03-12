from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from config import load_config
from orchestrator_client import OrchestratorClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
)
log = logging.getLogger(__name__)


async def main() -> None:
    config = load_config()

    intents = discord.Intents.default()
    intents.members = True  # needed for role lookup

    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready() -> None:
        assert bot.user is not None
        log.info("Logged in as %s (%d)", bot.user, bot.user.id)
        guild = discord.Object(id=config.guild_id)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        log.info("Synced %d command(s) to guild %d", len(synced), config.guild_id)

    @bot.tree.error
    async def on_app_command_error(
        interaction: discord.Interaction,
        error: Exception,
    ) -> None:
        log.exception("Unhandled app command error", exc_info=error)
        msg = "An unexpected error occurred. Please try again."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass

    async with OrchestratorClient(
        config.orchestrator_url, config.orchestrator_api_key
    ) as client:
        from cogs.dcs import DcsCog
        from cogs.events import EventsCog

        async with bot:
            await bot.add_cog(DcsCog(config, client, bot))
            await bot.add_cog(EventsCog(config))
            await bot.start(config.discord_token)


if __name__ == "__main__":
    asyncio.run(main())
