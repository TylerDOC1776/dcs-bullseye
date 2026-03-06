# Goonfront Strategic Expansion System

## Overview

Large-scale tug-of-war campaign on Caucasus map.

Map Layout:
- 30nm x 30nm sectors
- Rectangular grid zones
- Frontline push system

---

## Mechanics

Teams:
- Capture adjacent zones
- Drop troops
- Defend captured sectors
- Earn points over time

---

## Zone System

Data-driven:
Zones_Caucasus.lua
Pre-generated ZoneCommander entries.

Requirements:
- Correct rectangle drawing
- Ownership state
- Alignment correction

---

## Gameplay Loop

1. Deploy troops via CTLD
2. Infantry auto-run to nearest capture zone
3. Zone flips when contested threshold met
4. Points accumulate
5. Defensive assets spawn

---

## Scaling Difficulty

Spawnable missions:
- Escort
- Strike
- SEAD
- Defense

Dynamic escalation based on:
- Zone control %
- Player count
- Time held

---

## Long-Term Goals

- Multiple maps
- JSON zone definition loader
- Campaign persistence
- Web dashboard

---

## CLI Migration

zone generate
zone validate
zone export
mission build