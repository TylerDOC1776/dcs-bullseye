# Community Host Setup Guide

## Before You Start

1. **Install DCS World Dedicated Server**
   Download from the [Eagle Dynamics website](https://www.digitalcombatsimulator.com/en/downloads/world/server/).

2. **Run DCS server at least once**
   Launch it, let it get to the main menu or start a mission, then close it.
   This creates the Saved Games profile the installer needs to find.

---

## Install the Agent

Get your invite command from the server admin via Discord. It will look like this:

```powershell
$f="$env:TEMP\install-agent.ps1"; iwr -UseBasicParsing https://your-orchestrator.example.com/install/install.ps1 -OutFile $f; powershell -ExecutionPolicy Bypass -File $f -InviteCode GOON-XXXX-XXXX-XXXX -OrchestratorUrl https://your-orchestrator.example.com
```

The command downloads the installer to a temporary file and runs it — you can open the file in Notepad to inspect it before running if you prefer.

1. Open **PowerShell as Administrator**
2. Paste and run the command
3. Follow any prompts (it will ask you to confirm the DCS install path if it can't find it automatically)

The installer handles everything automatically:
- Downloads and installs the DCS Agent
- Creates your Active Missions folder
- Sets up the tunnel back to the central server
- Registers your host so it appears in Discord
- Installs the DCS Lua status hook

---

## Mission Files

Your Active Missions folder is created automatically at:
```
C:\Users\[you]\Saved Games\[DCS profile]\Active Missions\
```

Drop `.miz` files here and they'll show up in `/dcs mission`. If the folder already exists, the installer leaves it and its contents untouched.

---

## After Install

- Your server will appear in Discord and can be controlled via `/dcs start`, `/dcs stop`, etc.
- The DCSAgent and tunnel services start automatically on Windows boot.
- **Restart DCS after install** so the Lua status hook activates (enables live player/mission info in Discord).

---

## Updating the Agent

If the server admin pushes an update, run this in **PowerShell as Administrator**:

```powershell
$f="$env:TEMP\install-agent.ps1"; iwr -UseBasicParsing https://your-orchestrator.example.com/install/install.ps1 -OutFile $f; powershell -ExecutionPolicy Bypass -File $f -Update -OrchestratorUrl https://your-orchestrator.example.com
```

This pulls the latest agent code and restarts the service. No re-registration needed.
