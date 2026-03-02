from discord.ext import commands
from server_control import control_dcs_instance, is_instance_running
from config_loader import load_config
from load_miz import upload_mission_only
from datetime import datetime
from globals import config, start_times
import os
import re
import time
import subprocess
import psutil
import asyncio
import shutil

config = load_config()

user_mission_selection = {}
list_cache = {
    "instance_id": None,
    "missions": []
}


LOG_DIR = "C:\\DCSAdminBot\\Logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "bot_actions.log")

FATAL_KEYWORDS = ["Access violation", "Unhandled exception"]
DCS_PROCESS_NAME = "DCS_server"
last_known_state = {k: True for k in config["SERVERS"]}

def log_bot_action(message: str):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {message}\n")

def resolve_instance_name(key):
    return config["SERVERS"].get(key, {}).get("name")
   
def get_server_info(instance_id):
    instance = config["SERVERS"].get(instance_id)
    if not instance:
        return ("Unknown.miz", "?", "?")

    instance_name = instance["name"]
    settings_path = os.path.join(config["DCS_SAVED_GAMES"], instance_name, "Config", "serverSettings.lua")

    mission_name = "Unknown"
    port = "?"
    password = "?"

    if not os.path.exists(settings_path):
        return (mission_name, port, password)

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            for line in f:
                if ".miz" in line and '"' in line:
                    parts = line.strip().split('"')
                    for p in parts:
                        if p.endswith(".miz"):
                            mission_name = os.path.basename(p)
                elif "port" in line:
                    match = re.search(r'\["port"\]\s*=\s*"?(?P<port>\d+)"?', line)
                    if match:
                        port = match.group("port")

                    if match:
                        port = match.group(1)
                elif re.search(r'\["password"\]', line):
                    match = re.search(r'\["password"\]\s*=\s*"([^"]*)"', line)
                    if match:
                        password = match.group(1)
    except Exception:
        pass

    return (mission_name, port, password)
        
async def delete_cached_list_message(ctx):
    msg_id = list_cache.get("message_id")
    if msg_id:
        try:
            old_msg = await ctx.channel.fetch_message(msg_id)
            await old_msg.delete()
        except Exception as e:
            print(f"⚠️ Failed to delete cached mission list message: {e}")
        list_cache.pop("message_id", None)

def register_commands(bot):
    @bot.command()
    async def start(ctx, target: str):
        if ctx.channel.id != config['COMMAND_CHANNEL_ID']:
            return

        friendly_name = resolve_instance_name(target.lower())
        if not friendly_name:
            await ctx.send(f"❌ Unknown server: `{target}`")
            return

        await ctx.send(f"🚀 Starting `{friendly_name}`...")

        if control_dcs_instance(friendly_name, "start"):
            await ctx.send(f"✅ `{friendly_name}` started successfully.")
            log_bot_action(f"{ctx.author} ran !start {target} ({friendly_name})")
        else:
            await ctx.send(f"❌ Failed to start `{friendly_name}`.")
            log_bot_action(f"{ctx.author} failed to !start {target} ({friendly_name})")

    @bot.command()
    async def stop(ctx, target: str):
        if ctx.channel.id != config['COMMAND_CHANNEL_ID']:
            return

        friendly_name = resolve_instance_name(target.lower())
        if not friendly_name:
            await ctx.send(f"❌ Unknown server: `{target}`")
            return

        await ctx.send(f"🛑 Stopping `{friendly_name}`...")

        if control_dcs_instance(friendly_name, "stop"):
            await ctx.send(f"✅ `{friendly_name}` stopped successfully.")
            log_bot_action(f"{ctx.author} ran !stop {target} ({friendly_name})")
        else:
            await ctx.send(f"❌ Failed to stop `{friendly_name}`.")
            log_bot_action(f"{ctx.author} failed to !stop {target} ({friendly_name})")

    @bot.command()
    async def restart(ctx, target: str):
        if ctx.channel.id != config['COMMAND_CHANNEL_ID']:
            return

        if target.lower() == "all":
            await ctx.send("♻️ Restarting all DCS instances...")
            os.system(f'powershell -ExecutionPolicy Bypass -File "Scripts/DCSManage.ps1" -Action restart')
            await ctx.send("✅ All DCS instances restarted.")
            log_bot_action(f"{ctx.author} ran !restart all")
            return

        if target.lower() == "windows":
            await ctx.send("⚠️ Rebooting Windows in 5 seconds...")
            subprocess.run(["shutdown", "/r", "/t", "5"])
            log_bot_action(f"{ctx.author} triggered !restart windows")
            return

        friendly_name = resolve_instance_name(target.lower())
        if not friendly_name:
            await ctx.send(f"❌ Unknown server: `{target}`")
            return

        await ctx.send(f"♻️ Restarting `{friendly_name}`...")

        if control_dcs_instance(friendly_name, "restart"):
            await ctx.send(f"✅ `{friendly_name}` restarted successfully.")
            log_bot_action(f"{ctx.author} ran !restart {target} ({friendly_name})")
        else:
            await ctx.send(f"❌ Failed to restart `{friendly_name}`.")
            log_bot_action(f"{ctx.author} failed to !restart {target} ({friendly_name})")


    @bot.command()
    async def status(ctx):
        if ctx.channel.id != config["COMMAND_CHANNEL_ID"]:
            return

        await ctx.send("📡 DCS Server Status:")

        debug_msgs = []

        for instance_id, instance_data in config["SERVERS"].items():
            try:
                instance_name = instance_data["name"]
                debug_msgs.append(f"🔧 Checking {instance_name} (ID: {instance_id})")

                running = is_instance_running(instance_name)
                status = "✅ Running" if running else "❌ Not Running"

                uptime_msg = ""
                if running and instance_name in start_times:
                    uptime_sec = int(time.time() - start_times[instance_name])
                    hours, remainder = divmod(uptime_sec, 3600)
                    minutes, _ = divmod(remainder, 60)
                    uptime_msg = f" (Uptime: {hours}h {minutes}m)"

                mission, port, password = get_server_info(instance_id)
                debug_msgs.append(
                    f"`{instance_name}`: {status}{uptime_msg} | 🎯 `{mission}` | 🔌 Port: `{port}` | 🔒 Password: `{password}`"
)


            except Exception as e:
                debug_msgs.append(f"❌ Error processing `{instance_id}`: {e}")

        # Send debug output in one shot
        for chunk in debug_msgs:
            await ctx.send(chunk)

    @bot.command()
    async def clear(ctx):
        if ctx.channel.id != config['COMMAND_CHANNEL_ID']:
            return

        await ctx.send("🪟 Clearing bot messages and commands...")
        deleted = 0

        command_keywords = [
            "!start", "!stop", "!restart", "!status", "!clear", "!help",
            "!loadmiz", "!resetpersist", "!resetstats", "!listmissions", "!choose", 
            "!changepass", "!delete"
        ]

        emoji_keywords = ["✅", "🛑", "📦", "♻️", "📊", "📄", "🧾", "🪟", "📱", "❌", "🩾"]

        async for msg in ctx.channel.history(limit=200):
            if (
                msg.author == bot.user or
                any(msg.content.startswith(cmd) for cmd in command_keywords) or
                any(sym in msg.content for sym in emoji_keywords)
            ):
                try:
                    await msg.delete()
                    deleted += 1
                except Exception as e:
                    print(f"⚠️ Could not delete message: {e}")

        await ctx.send(f"✅ Cleared {deleted} bot-related messages.")
        log_bot_action(f"{ctx.author} ran !clear and removed {deleted} messages")


    @bot.command()
    async def loadmiz(ctx):
        if ctx.channel.id != config['COMMAND_CHANNEL_ID']:
            return
        if not ctx.message.attachments:
            await ctx.send("❌ Please attach a `.miz` file.")
            return

        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith('.miz'):
            await ctx.send("❌ Invalid file type. Only `.miz` files are accepted.")
            return

        try:
            if attachment.size > 30 * 1024 * 1024:
                await ctx.send("❌ File too large. Max size is 30 MB.")
                return

            file_bytes = await attachment.read()
            from load_miz import upload_mission_only
            success, msg = upload_mission_only(attachment.filename, file_bytes)
            await ctx.send(f"✅ {msg}" if success else f"❌ {msg}")
            log_bot_action(f"{ctx.author} uploaded and saved mission `{attachment.filename}` to Active Missions")

        except Exception as e:
            await ctx.send(f"❌ Failed to process file: {e}")
            log_bot_action(f"[ERROR] {ctx.author} failed !loadmiz: {e}")

    @bot.command()
    async def changepass(ctx, target: str, new_password: str):
        if ctx.channel.id != config["COMMAND_CHANNEL_ID"]:
            return

        results = []
        target = target.lower()
        targets = [target] if target in config["SERVERS"] else (config["SERVERS"].keys() if target == "all" else [])

        if not targets:
            await ctx.send(f"❌ Unknown server `{target}`. Try `southern`, `memphis`, `smokey`, or `all`.")
            return

        for instance_id in targets:
            instance = config["SERVERS"][instance_id]
            instance_name = instance["name"]
            settings_path = os.path.join(config["DCS_SAVED_GAMES"], instance_name, "Config", "serverSettings.lua")

            if not os.path.exists(settings_path):
                results.append(f"❌ `{instance_name}`: serverSettings.lua not found.")
                continue

            try:
                updated = False
                updated_lines = []

                with open(settings_path, "r", encoding="utf-8") as f:
                    for line in f:
                        #print("🔍 LINE:", repr(line))  # DEBUG PRINT

                        if '["password"]' in line:
                            print("✅ MATCHED password line")
                            prefix = line.split("=")[0]
                            newline = f'{prefix}= "{new_password}",\n'
                            #print("✏️ NEW LINE:", repr(newline))  # DEBUG PRINT
                            updated_lines.append(newline)
                            updated = True
                        else:
                            updated_lines.append(line)

                with open(settings_path, "w", encoding="utf-8") as f:
                    f.writelines(updated_lines)

                if updated:
                    results.append(f"🔐 `{instance_name}` password updated, use !restart`{instance_name}` to complete")
                else:
                    results.append(f"⚠️ `{instance_name}`: No password line found.")

            except Exception as e:
                results.append(f"❌ `{instance_name}`: {e}")

        await ctx.send("\n".join(results))


    @bot.command()
    async def resetpersist(ctx, instance: str):
        if ctx.channel.id != config['COMMAND_CHANNEL_ID']:
            return

        full_name = resolve_instance_name(instance)
        if not full_name:
            await ctx.send(f"❌ Unknown server: `{instance}`")
            return

        try:
            save_dir = os.path.join(
                config["DCS_SAVED_GAMES"],
                full_name,
                "Missions",
                "Saves"
            )

            if not os.path.exists(save_dir):
                await ctx.send(f"❌ Save folder not found: `{save_dir}`")
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            backup_dir = os.path.join(save_dir, f"Backup_{timestamp}")
            os.makedirs(backup_dir, exist_ok=True)

            count = 0
            for file in os.listdir(save_dir):
                if file.lower().endswith((".json", ".lua", ".csv")):
                    shutil.move(os.path.join(save_dir, file), os.path.join(backup_dir, file))
                    count += 1

            await ctx.send(f"♻️ `{instance}` persistence reset. {count} file(s) backed up to `Backup_{timestamp}`.")
            log_bot_action(f"{ctx.author} reset persistence for {instance}, moved {count} files to backup.")

        except Exception as e:
            await ctx.send(f"❌ Error: {e}")
            log_bot_action(f"[ERROR] {ctx.author} failed !resetpersist: {e}")

    @bot.command()
    async def resetstats(ctx, instance: str):
        if ctx.channel.id != config['COMMAND_CHANNEL_ID']:
            return

        full_name = resolve_instance_name(instance)
        if not full_name:
            await ctx.send(f"❌ Unknown server: `{instance}`")
            return

        try:
            save_dir = os.path.join(
                config["DCS_SAVED_GAMES"],
                full_name,
                "EasyStatsPlus",
                "MyMission"
            )

            if not os.path.exists(save_dir):
              await ctx.send(f"❌ Stats directory not found: `{save_dir}`")
              return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = save_dir + "_backup_" + timestamp
            os.rename(save_dir, backup_dir)


            await ctx.send(f"📊 `{instance}` stats reset. Original folder renamed to `{backup_dir}`.")
            log_bot_action(f"{ctx.author} reset stats for {instance}, renamed to {backup_dir}")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")
            log_bot_action(f"[ERROR] {ctx.author} failed !resetstats: {e}")

    @bot.command()
    async def listmissions(ctx):
        if ctx.channel.id != config["COMMAND_CHANNEL_ID"]:
            return

        mission_dir = config["DCS_ACTIVE_MISSIONS"]

        if not os.path.exists(mission_dir):
            await ctx.send("❌ Active Missions folder not found.")
            return

        try:
            files = os.listdir(mission_dir)
            missions = [f for f in files if f.lower().endswith(".miz")]

            if not missions:
                await ctx.send("📭 No mission files found in Active Missions.")
                return

            list_cache["missions"] = missions

            msg_lines = ["📂 Missions in `Active Missions`:"]
            for i, m in enumerate(missions, 1):
                msg_lines.append(f"`{i}`. {m}")
            msg_lines.append("\n➡️ Use `!choose <#> <server>` to load a mission")
            msg_lines.append("🗑️ Use `!delete <#>` to remove and back it up")

            message = await ctx.send("\n".join(msg_lines))
            list_cache["message_id"] = message.id  # Store the message ID to delete later

        except Exception as e:
            print("❌ Exception in listmissions:", e)
            await ctx.send(f"❌ Error while reading mission folder: {e}")


    @bot.command()
    async def choose(ctx, number: int, server: str):
        if ctx.channel.id != config['COMMAND_CHANNEL_ID']:
            return

        from load_miz import update_mission_list, get_instance_name
        from server_control import control_dcs_instance

        if "missions" not in list_cache:
            await ctx.send("❌ You must run `!listmissions` first.")
            return

        server = server.lower()
        if server not in config["SERVERS"]:
            await ctx.send(f"❌ Unknown server: `{server}`")
            return

        missions = list_cache["missions"]
        if number < 1 or number > len(missions):
            await ctx.send("❌ Invalid mission number.")
            return

        try:
            selected_file = missions[number - 1]
            instance_name = get_instance_name(server)
            full_path = os.path.join(config["DCS_ACTIVE_MISSIONS"], selected_file)

            if not os.path.exists(full_path):
                await ctx.send(f"❌ File not found: `{selected_file}` in Active Missions")
                return

            updated, update_msg = update_mission_list(instance_name, full_path)

            if updated:
                await ctx.send(f"📦 Selected mission: `{selected_file}`\n{update_msg}")
                await ctx.send(f"♻️ Restarting `{instance_name}` to load new mission...")
                if control_dcs_instance(instance_name, "restart"):
                    await ctx.send(f"✅ `{instance_name}` restarted with new mission.")
                    await delete_cached_list_message(ctx)
                else:
                    await ctx.send(f"❌ Failed to restart `{instance_name}`.")
            else:
                await ctx.send(f"❌ Failed to update mission list: {update_msg}")

        except Exception as e:
            await ctx.send(f"❌ Error switching mission: {e}")
    
    @bot.command()
    async def delete(ctx, index: int):
        if ctx.channel.id != config["COMMAND_CHANNEL_ID"]:
            return

        if "missions" not in list_cache:
            await ctx.send("⚠️ Run `!listmissions` first.")
            return

        try:
            missions = list_cache["missions"]
            if index < 1 or index > len(missions):
                await ctx.send(f"❌ Index out of range. Valid range: 1 to {len(missions)}")
                return

            mission_to_remove = missions[index - 1]
            mission_path = os.path.join(config["DCS_ACTIVE_MISSIONS"], mission_to_remove)
            backup_dir = os.path.join(config["DCS_ACTIVE_MISSIONS"], "Backup_Missions")
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, mission_to_remove)
            await delete_cached_list_message(ctx)

            if not os.path.exists(mission_path):
                await ctx.send(f"❌ Mission file `{mission_to_remove}` not found.")
                return

            os.rename(mission_path, backup_path)

            await ctx.send(f"🗑️ `{mission_to_remove}` has been deleted and backed up.")
            list_cache["missions"] = []  # Clear cached list

        except Exception as e:
            await ctx.send(f"❌ Failed to delete mission: {e}")

    @bot.command()
    async def help(ctx):
        if ctx.channel.id != config['COMMAND_CHANNEL_ID']:
            return
        help_text = """🩾 **DCS Admin Bot Commands:**

`!start <server>` - Start a DCS instance
`!stop <server>` - Stop a DCS instance
`!restart <server|all|windows>` - Restart a DCS instance, all, or reboot the system
`!changepass <server|all>` - Change the password for one or all servers
`!loadmiz <server>` - Upload a `.miz` mission file
`!resetpersist <server>` - Backup and delete persistence files for fresh mission start
`!resetstats <server>` - Rename EasyStatsPlus stats folder for a clean start
`!listmissions` - List available `.miz` missions from the Active Missions folder
`!choose <number> <server>` - Load one of the listed missions onto a server
`!delete <number> ` - Delete miz file from listed missions
`!status` - Show current server status
`!clear` - Delete all previous bot messages
`!help` - Show this help message"""
        await ctx.send(help_text)
        log_bot_action(f"{ctx.author} ran !help")
