#Requires -Version 5.1
<#
.SYNOPSIS
    Start the DCS platform services in development mode.

.DESCRIPTION
    Launches the orchestrator and Discord bot in separate terminal windows.
    Requires a populated .env in discord-bot/ and a valid orchestrator config.

.PARAMETER OrchestratorConfig
    Path to orchestrator JSON config. Defaults to configs\orchestrator.example.json.

.PARAMETER AgentConfig
    Path to agent JSON config (optional, for testing agent locally).

.EXAMPLE
    .\scripts\dev.ps1
    .\scripts\dev.ps1 -OrchestratorConfig C:\configs\my-orchestrator.json
#>

param(
    [string]$OrchestratorConfig = "$PSScriptRoot\..\configs\orchestrator.example.json",
    [switch]$IncludeAgent
)

$Root = Resolve-Path "$PSScriptRoot\.."

function Start-ServiceWindow {
    param([string]$Title, [string]$WorkDir, [string]$Command)
    Start-Process powershell -ArgumentList "-NoExit", "-Command",
        "cd '$WorkDir'; `$Host.UI.RawUI.WindowTitle = '$Title'; $Command"
}

Write-Host "Starting DCS platform (dev mode)..." -ForegroundColor Cyan

# Orchestrator
$env:DCS_ORCHESTRATOR_CONFIG = (Resolve-Path $OrchestratorConfig).Path
Start-ServiceWindow `
    -Title "DCS Orchestrator" `
    -WorkDir "$Root\orchestrator" `
    -Command "python -m orchestrator serve"

Start-Sleep -Milliseconds 1500   # give orchestrator a moment to bind

# Discord bot
Start-ServiceWindow `
    -Title "DCS Discord Bot" `
    -WorkDir "$Root\discord-bot" `
    -Command "python bot.py"

# Optional: local agent
if ($IncludeAgent) {
    Start-ServiceWindow `
        -Title "DCS Agent" `
        -WorkDir "$Root\agent" `
        -Command "python -m agent serve"
}

Write-Host "Services launched in separate windows." -ForegroundColor Green
Write-Host "  Orchestrator: http://localhost:8888/health"
Write-Host "  Agent (if started): http://localhost:8787/health"
