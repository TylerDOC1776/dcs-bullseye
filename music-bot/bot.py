import asyncio
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))
BOT_CHANNEL_ID = int(os.getenv('BOT_CHANNEL_ID', 0))

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot.log'), encoding='utf-8'),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger('larabot')

intents = discord.Intents.default()
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)


async def check_bot_channel(interaction: discord.Interaction) -> bool:
    if BOT_CHANNEL_ID and interaction.channel_id != BOT_CHANNEL_ID:
        await interaction.response.send_message(
            f'Please use <#{BOT_CHANNEL_ID}> for bot commands.', ephemeral=True
        )
        return False
    return True


bot.tree.interaction_check = check_bot_channel


@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    log.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    log.info('Slash commands synced.')


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: Exception):
    log.error(f'Command error in {interaction.command.name if interaction.command else "unknown"}: {error}', exc_info=error)
    if not interaction.response.is_done():
        await interaction.response.send_message('An unexpected error occurred.', ephemeral=True)


async def main():
    async with bot:
        await bot.load_extension('cogs.music')
        await bot.load_extension('cogs.playlists')
        await bot.start(TOKEN)


asyncio.run(main())
