# Future Features

## Completed

| Feature | Notes |
|---------|-------|
| ~~Player join/leave notifications~~ ✅ | Analytics pipeline — agent pushes events to orchestrator every 60s |
| ~~Alerts when a server crashes repeatedly~~ ✅ | Crash loop detection in EventsCog — 3 crashes/10 min triggers alert |
| ~~Player count history / analytics~~ ✅ | `/dcs stats` — sessions, players, missions, maps, peak hours (EST/PST) |
| ~~Player self-service stats~~ ✅ | `/dcs register` + `/dcs mystats` — personal stats per pilot name |
| ~~Per-player session duration tracking~~ ✅ | Session pairing (join→leave) — avg and total time in `/dcs mystats`, avg in `/dcs stats` |

---

## Planned

| # | Feature | Difficulty | Notes |
|---|---------|------------|-------|
| 1 | Community host status in embed | Medium | Show external servers configured without an agent with richer info beyond TCP ping — already shown in status embed but could be improved |
| 2 | Auto-update schedule | Medium | Run DCS update automatically at a configured time instead of manual `/dcs update` trigger |
| 3 | Scheduled mission rotation | Medium | Auto-cycle through a mission playlist on a timer — configurable per instance |
| 4 | Mission vote / rotation command | Hard | Let players vote to change the active mission via Discord; majority wins |
| 5 | Player join/leave Discord notifications | Medium | Post a message when a player joins or leaves a server (requires threshold to avoid spam) |
| 6 | Analytics retention / pruning | Easy | Auto-delete analytics events older than N days to keep DB small |
| 7 | `/dcs stats` trend comparison | Medium | Compare this week vs last week for player counts and activity |
