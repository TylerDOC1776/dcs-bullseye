# Notes

## FastAPI / NSSM

use FastAPI

will need to be on NSSM

---

## Monorepo Target Structure

DCS-MonoRepo/
├─ README.md
├─ LICENSE
├─ .gitignore
├─ docs/
│  ├─ 00-Repo-Overview.md
│  ├─ 01-DCS-Service-Bot-Architecture.md
│  ├─ 02-DCS-Adaptive-Defense-System.md
│  ├─ 03-DCS-Docker-Benchmark.md
│  ├─ 04-DCS-Goonfront-Strategic-Expansion.md
│  ├─ 05-DCS-Community-Host-Installer.md
│  └─ 90-Roadmap.md
├─ packages/
│  ├─ shared/
│  │  ├─ README.md
│  │  ├─ src/
│  │  │  ├─ config/
│  │  │  ├─ logging/
│  │  │  ├─ process/
│  │  │  ├─ net/
│  │  │  ├─ time/
│  │  │  └─ types/
│  │  └─ tests/
│  ├─ cli/
│  │  ├─ README.md
│  │  ├─ src/
│  │  │  ├─ commands/
│  │  │  │  ├─ host/
│  │  │  │  ├─ agent/
│  │  │  │  ├─ server/
│  │  │  │  ├─ benchmark/
│  │  │  │  └─ mission/
│  │  │  ├─ index.ts
│  │  │  └─ ui/
│  │  └─ tests/
│  ├─ orchestrator/
│  │  ├─ README.md
│  │  ├─ src/
│  │  │  ├─ api/
│  │  │  ├─ auth/
│  │  │  ├─ router/
│  │  │  ├─ registry/
│  │  │  ├─ scheduler/
│  │  │  ├─ telemetry/
│  │  │  └─ storage/
│  │  └─ tests/
│  ├─ agent/
│  │  ├─ README.md
│  │  ├─ src/
│  │  │  ├─ runtime/
│  │  │  ├─ nssm/
│  │  │  ├─ dcs/
│  │  │  ├─ logs/
│  │  │  ├─ updater/
│  │  │  ├─ metrics/
│  │  │  └─ api/
│  │  └─ tests/
│  ├─ benchmark/
│  │  ├─ README.md
│  │  ├─ src/
│  │  │  ├─ runners/
│  │  │  ├─ probes/
│  │  │  ├─ scenarios/
│  │  │  ├─ collectors/
│  │  │  └─ reports/
│  │  └─ tests/
│  ├─ missions/
│  │  ├─ README.md
│  │  ├─ adaptive-defense/
│  │  │  ├─ README.md
│  │  │  ├─ miz/
│  │  │  └─ lua/
│  │  │     ├─ PlayerScanner.lua
│  │  │     ├─ RoleClassifier.lua
│  │  │     ├─ ResponseSpawner.lua
│  │  │     └─ ThreatScaler.lua
│  │  ├─ goonfront/
│  │  │  ├─ README.md
│  │  │  ├─ miz/
│  │  │  ├─ lua/
│  │  │  └─ zones/
│  │  │     ├─ Zones_Caucasus.lua
│  │  │     └─ Zones_Caucasus.json
│  │  └─ tools/
│  │     ├─ README.md
│  │     ├─ zone-generate/
│  │     ├─ zone-validate/
│  │     └─ mission-build/
│  ├─ installer/
│  │  ├─ README.md
│  │  ├─ src/
│  │  │  ├─ windows/
│  │  │  ├─ dcs/
│  │  │  ├─ nssm/
│  │  │  ├─ agent/
│  │  │  ├─ config/
│  │  │  └─ register/
│  │  └─ tests/
│  └─ discord-bot/
│     ├─ README.md
│     ├─ src/
│     │  ├─ commands/
│     │  ├─ permissions/
│     │  ├─ formatting/
│     │  └─ transport/
│     └─ tests/
├─ configs/
│  ├─ orchestrator.example.json
│  ├─ agent.example.json
│  ├─ server.example.json
│  └─ benchmark.example.json
├─ scripts/
│  ├─ dev.ps1
│  ├─ dev.sh
│  ├─ build.ps1
│  ├─ build.sh
│  ├─ test.ps1
│  ├─ test.sh
│  └─ release.ps1
└─ infra/
   ├─ docker/
   ├─ tailscale/
   ├─ nginx/
   └─ systemd/   (future linux native)