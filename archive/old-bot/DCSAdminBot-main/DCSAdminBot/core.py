import asyncio
import discord
import psutil
from discord.ext import commands
from globals import config, start_times
from log_monitor import background_task
from commands import register_commands

def populate_start_times():
    for proc in psutil.process_iter(['name', 'cmdline', 'create_time']):
        if proc.info['name'] == 'DCS_server.exe':
            cmd = " ".join(proc.info.get("cmdline", []))
            for instance_id, instance in config["SERVERS"].items():
                if f"-w {instance['name']}" in cmd:
                    start_times[instance["name"]] = proc.info["create_time"]
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all(), help_command=None)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    channel = bot.get_channel(config['COMMAND_CHANNEL_ID'])
    if channel:
        await channel.send("📡 DCS Admin Bot is online and ready.")

def run_bot():
    register_commands(bot)
    populate_start_times()
    asyncio.run(main())

async def main():
    asyncio.create_task(background_task(bot))
    await bot.start(config['DISCORD_BOT_TOKEN'])
if __name__ == "__main__":
    run_bot()
