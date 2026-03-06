# DCS Community Host Installer

## Goal

Allow anyone to:

1. Install DCS server
2. Install bot agent
3. Register to central command
4. Deploy multi-server instance

With minimal manual configuration.

---

## Components

Installer does:

- Install DCS Dedicated
- Create Saved Games structure
- Configure ports
- Install NSSM service
- Install Agent
- Generate config.json
- Register with central bot

---

## Configuration

Config-driven:
{
  "server_name": "",
  "instance_id": "",
  "ports": {},
  "auth_token": ""
}

---

## Security

- Token-based authentication
- Rate limiting
- Command validation

---

## Future

- Auto TLS
- Remote update push
- Self-healing agent

---

## CLI Structure

dcs-host install
dcs-host register
dcs-host update
dcs-host status