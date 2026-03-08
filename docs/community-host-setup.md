# Community Host Setup Guide

## Prerequisites

The platform VPS must already be running before community hosts can join. If you are the platform admin and haven't set up the VPS yet, run `scripts/install-vps.sh` first — see the [VPS Setup wiki page](https://github.com/TylerDOC1776/dcs-bullseye/wiki/VPS-Setup).

---

## Before You Start

1. **Install DCS World Dedicated Server**
   Download from the [Eagle Dynamics website](https://www.digitalcombatsimulator.com/en/downloads/world/server/).

2. **Run DCS server at least once**
   Launch it, let it get to the main menu or start a mission, then close it.
   This creates the Saved Games profile the installer needs to find.

---

## Install the Agent

Get your invite code from the server admin via Discord — they will send you the complete install command. It looks like this:

```powershell
$f="$env:TEMP\install-agent.ps1"; iwr -UseBasicParsing <ORCHESTRATOR_URL>/install/install.ps1 -OutFile $f; powershell -ExecutionPolicy Bypass -File $f -InviteCode GOON-XXXX-XXXX-XXXX -OrchestratorUrl <ORCHESTRATOR_URL>
```

Run the exact command the admin sends you — don't modify the URL or invite code.

Follow any prompts (it will ask for a host name and confirm the DCS install path if it can't find it automatically).

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

If the server admin pushes an update, run this in **PowerShell as Administrator** (replace `<ORCHESTRATOR_URL>` with the URL from your original install command):

```powershell
$f="$env:TEMP\install-agent.ps1"; iwr -UseBasicParsing <ORCHESTRATOR_URL>/install/install.ps1 -OutFile $f; powershell -ExecutionPolicy Bypass -File $f -Update
```

This pulls the latest agent code and restarts the service. No re-registration needed.
