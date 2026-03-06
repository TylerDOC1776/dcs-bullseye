# DCS Multi-Server Service & Central Bot Architecture

## Overview
Transition DCS dedicated servers to run as Windows services (via NSSM), and redesign the Discord bot into a centralized command router capable of managing multiple remote DCS servers.

Goal: Turn DCS hosting into a scalable, self-managing infrastructure that others can easily deploy.

---

## Core Problems Identified

1. WebGUI only accessible locally.
2. Running 3 servers on one Windows 11 machine causes conflicts.
3. Behind CGNAT → requires Tailscale + VPS relay endpoint.
4. Bot tightly coupled to single-instance server logic.
5. Manual intervention required for DCS updates.
6. No uptime tracking.
7. No automated service monitoring.

---

## Architecture Plan

### 1. Run DCS as a Windows Service
- Use NSSM to wrap DCS.exe
- Independent service per server instance
- Unique:
  - Saved Games folders
  - Ports
  - WebGUI ports
- Add service health monitoring

Bot Commands:
- /status
- /restart
- /stop
- /start
- /uptime

---

### 2. Central Command Router Bot (Next Gen Bot)

New Architecture:

Discord → Central Bot → Agent Clients → DCS Servers

Each server runs a lightweight agent that:
- Accepts authenticated commands
- Executes:
  - NSSM control
  - Log pull
  - Mission load
  - Restart
  - Update
- Returns structured JSON

Transport Options:
- REST API (preferred)
- WebSocket
- gRPC (future)

---

### 3. WebGUI Remote Access Fix

Options:
- Reverse proxy per instance
- NGINX on VPS via Tailscale
- SSH tunnel automation
- Port isolation validation

Ensure:
- No WebGUI port collisions
- Unique instance binding

---

### 4. Auto Update Without Human Click

Investigate:
- DCS_updater.exe CLI flags
- Silent update switch
- Scheduled maintenance window
- Stop service → Update → Start service

Bot Integration:
- /update all
- /update server1

---

### 5. Uptime Logging

Add:
- Timestamp log when service starts
- Store in persistent JSON
- On query:
  - Calculate uptime
  - Return formatted duration

---

### 6. Error Log Pull

Bot command:
- /log latest
- /log errors
- /log crash

Implementation:
- Parse dcs.log
- Extract ERROR and WARNING
- Send formatted output

---

## Long-Term Goals

- Easy installer for community hosts
- Config-driven multi-server deploy
- Self-healing service model
- Update orchestration across nodes
- Horizontal scaling support

---

## CLI Migration Plan

Repo Structure:

/core
/agents
/services
/config
/logging
/bot

Move from monolithic bot → modular service architecture.