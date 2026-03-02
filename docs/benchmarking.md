# DCS Docker vs Native Performance Benchmark

## Goal

Objectively measure performance differences between:

1. Windows 11 Native
2. WSL + Docker Container
3. Potential Linux Native (future)

---

## Metrics to Measure

- CPU usage
- RAM usage
- Mission load time
- AI tick performance
- Script execution timing
- Network latency
- Stability over 24hr run

---

## Test Framework Plan

Automated script that:

1. Launches DCS
2. Loads identical mission
3. Runs timed AI simulation
4. Logs:
   - CPU
   - RAM
   - FPS (if applicable)
   - Script execution duration
5. Dumps JSON results

---

## Tools

- PowerShell for Windows metrics
- Docker stats
- Windows Performance Counters
- Lua timer logs

---

## Output

Produce:
- CSV results
- JSON comparison
- Summary report

---

## Decision Criteria

Container worth it if:
- ≤10% performance loss
- Improved isolation
- Easier scaling

---

## CLI Plan

Create:
benchmark run
benchmark compare
benchmark report