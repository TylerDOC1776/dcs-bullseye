import subprocess
import psutil
import os
import asyncio

def control_dcs_instance(instance_name, action, discord_channel=None):
    script_path = os.path.join(os.path.dirname(__file__), "Scripts", "DCSManage.ps1")

    if not os.path.exists(script_path):
        print(f"[ERROR] DCSManage.ps1 not found at {script_path}")
        return False

    ps_command = f"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; & '{script_path}' -Action '{action}' -Target '{instance_name}'"

    command = [
        "powershell.exe",
        "-ExecutionPolicy", "Bypass",
        "-Command", ps_command
    ]

    print(f"[INFO] Executing: powershell.exe -ExecutionPolicy Bypass -Command {ps_command}")

    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=120)

        if result.returncode != 0:
            print(f"[ERROR] DCSManage.ps1 exited with code {result.returncode}")
            if result.stderr:
                print(f"[stderr]\n{result.stderr}")
            if discord_channel:
                asyncio.run_coroutine_threadsafe(
                    discord_channel.send(f"❌ Failed to {action} {instance_name}. Script error."),
                    discord_channel.loop
                )
            return False

        if result.stdout.strip():
            print(f"[INFO] Script output:\n{result.stdout.strip()}")
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if discord_channel:
                    msg = ""
                    if line.startswith("STARTED"):
                        msg = f"✅ {line[8:]} started successfully."
                    elif line.startswith("STOPPED"):
                        msg = f"🛑 {line[8:]} stopped."
                    elif line.startswith("FAILED_START"):
                        msg = f"❌ Failed to start {line[13:]}"
                    elif line.startswith("FAILED_STOP"):
                        msg = f"❌ Failed to stop {line[12:]}"
                    elif line.startswith("NOT_RUNNING"):
                        msg = f"⚠️ No running instance of {line[12:]} found."
                    elif line.startswith("INVALID_TARGET"):
                        msg = f"❌ Invalid instance name: {line[15:]}"

                    if msg:
                        asyncio.run_coroutine_threadsafe(
                            discord_channel.send(msg),
                            discord_channel.loop
                        )

        return True

    except subprocess.TimeoutExpired:
        print(f"[ERROR] DCSManage.ps1 timed out after 120 seconds.")
        if discord_channel:
            asyncio.run_coroutine_threadsafe(
                discord_channel.send(f"❌ {instance_name} {action} timed out."),
                discord_channel.loop
            )
        return False

    except Exception as e:
        print(f"[EXCEPTION] Failed to execute DCSManage.ps1: {e}")
        if discord_channel:
            asyncio.run_coroutine_threadsafe(
                discord_channel.send(f"❌ Exception during {action} for {instance_name}: {e}"),
                discord_channel.loop
            )
        return False

def is_instance_running(name):
    for proc in psutil.process_iter(['name', 'cmdline']):
        if proc.info['name'] == "DCS_server.exe" and f"-w {name}" in " ".join(proc.info['cmdline']):
            return True
    return False
