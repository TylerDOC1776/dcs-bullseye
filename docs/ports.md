# Server Port Reference

## Main Servers (VPS → Tailscale → Windows)

| Server | DCS Game | Tacview | WebGUI |
|--------|----------|---------|--------|
| SouthernBBQ | 10308 | 42674 | 8088 |
| MemphisBBQ | 10309 | 42675 | — |
| SmokeyBBQ | 10310 | 42676 | 8091 |
| TexasBBQ | 10311 | 42677 | 8092 |

## Shared Services

| Service | Port | Protocol |
|---------|------|----------|
| SRS (Simple Radio) | 5002 | UDP + TCP |

## Community Hosts

| Server | DCS Game | Tacview | SRS |
|--------|----------|---------|-----|
| East Coast BBQ | | | |
| Taylor Ham BBQ | | | |

## frp Tunnel Ports (VPS)

| Use | Range |
|-----|-------|
| Community host agent tunnels | 8800 – 8899 |

## Internal Services (VPS, not public)

| Service | Port |
|---------|------|
| Orchestrator API | 8888 |
