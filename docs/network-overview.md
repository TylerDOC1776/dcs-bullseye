# Network Overview

## The Big Picture

```
  Your Discord Server
         │
         │  slash commands
         ▼
  ┌─────────────────┐
  │   Discord Bot   │         ← runs on the VPS
  └────────┬────────┘
           │  REST API (internal)
           ▼
  ┌─────────────────┐
  │  Orchestrator   │         ← runs on the VPS
  └────────┬────────┘
           │  frp tunnel (outbound from Windows, localhost only on VPS)
           ▼
  ┌─────────────────┐
  │   DCS Agent     │         ← runs on each Windows DCS machine
  └────────┬────────┘
           │  Windows service control (NSSM / Task Scheduler)
           ▼
  ┌─────────────────┐
  │   DCS Server    │         ← the actual game server process
  └─────────────────┘
```

---

## The VPS (Central Hub)

The VPS (your public IP) is the only machine that needs to be publicly reachable. It runs:

- **Orchestrator** — the REST API that stores host/instance records and relays commands to agents
- **Discord Bot** — receives slash commands and talks to the orchestrator
- **frp server** — accepts tunnel connections from Windows machines

The VPS does not run DCS. It only routes commands and stores configuration.

---

## The Windows DCS Machine

Each Windows machine runs:

- **DCS World** — the game server itself
- **DCS Agent** — a lightweight REST API that controls DCS (start/stop/mission load/etc.)
- **frp client** — maintains a persistent outbound tunnel to the VPS

The Windows machine does **not** need a public IP or open inbound firewall ports. It reaches out to the VPS, not the other way around.

---

## The Tunnel (frp)

The frp tunnel is how the orchestrator on the VPS reaches the agent on the Windows machine.

### How it works
1. When the Windows machine boots, the frp client connects outbound to the VPS on port `7000`
2. This creates a persistent reverse tunnel — the VPS gets a local port (e.g. `localhost:8800`) that forwards directly to the agent's REST API on the Windows machine
3. The orchestrator calls `localhost:8800` to send commands to that agent — the traffic never leaves the VPS

### What the tunnel carries
- **Control commands only** — start, stop, restart, mission load, log fetch, etc.
- Small payloads — mission files (upload/download), log bundles
- All traffic is authenticated with a token

### What the tunnel does NOT do
- **DCS game traffic does not go through the tunnel** — players connect directly to the Windows machine's public IP on the DCS game ports. The tunnel has nothing to do with player connectivity.
- **The tunnel cannot be used to access the Windows machine remotely** — it only exposes the agent's REST API, nothing else. No desktop, no file system browser, no shell access.
- **The tunnel is not a VPN** — only the specific agent port is forwarded, and it's bound to `localhost` on the VPS so it's never exposed to the internet.

### What happens if the tunnel drops
The agent on the Windows machine will keep DCS running normally. Players already in the server are unaffected. The bot will show the host as offline and commands will fail until the tunnel reconnects. The frp client reconnects automatically.

---

## Player Connectivity

Players connect directly to the Windows machine — the VPS and tunnel are not involved at all in game traffic.

```
  Player ──────────────────────────────► Windows DCS Machine
                 (direct connection)       port 10308 (game)
```

The Windows machine needs its DCS game ports open in the firewall/router as normal. The platform does not change this requirement.

---

## Security

- The tunnel uses token authentication — only frp clients with the correct token can connect
- The agent REST API requires an API key on every request — generated uniquely per host at registration time
- Tunnel ports are bound to `localhost` on the VPS only — they are not reachable from the internet
- The install one-liner requires a single-use invite code — each code can only register one host

---

## Capacity

The current setup supports up to **100 community hosts** (frp ports `8800–8899`). This can be expanded by the admin at any time by adjusting the port range in the frp server config.
