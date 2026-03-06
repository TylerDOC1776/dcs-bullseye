<#
.SYNOPSIS
    Stops all DCS instances, runs DCS_updater.exe, then restarts instances.

.DESCRIPTION
    Called by the DCS-UpdateDCS Task Scheduler task (runs as SYSTEM).
    Status is written to C:\ProgramData\DCSAgent\update_status.json
    so the DCS Agent REST API can report progress to Discord.

.PARAMETER ConfigFile
    Path to the agent config.json. Default: C:\DCSAgent\config.json
#>
param(
    [string]$ConfigFile = "C:\ProgramData\DCSAgent\config.json"
)

$StatusFile = "C:\ProgramData\DCSAgent\update_status.json"
$ErrorActionPreference = "Stop"

function Write-Status {
    param([string]$Phase, [bool]$Running, [string]$Message)
    @{
        phase      = $Phase
        running    = $Running
        message    = $Message
        updated_at = (Get-Date -Format "o")
    } | ConvertTo-Json | Set-Content -Path $StatusFile -Encoding UTF8
}

# Ensure status directory exists
New-Item -ItemType Directory -Force -Path (Split-Path $StatusFile) | Out-Null

try {
    Write-Status "starting" $true "Reading agent config..."

    if (-not (Test-Path $ConfigFile)) {
        Write-Status "failed" $false "Config not found: $ConfigFile"
        exit 1
    }

    $config    = Get-Content $ConfigFile -Raw | ConvertFrom-Json
    $instances = $config.instances

    if (-not $instances -or $instances.Count -eq 0) {
        Write-Status "failed" $false "No instances found in config"
        exit 1
    }

    # Derive updater path from first instance exe_path
    $updaterPath = $instances[0].exe_path -replace "DCS_server\.exe$", "DCS_updater.exe"

    if (-not (Test-Path $updaterPath)) {
        Write-Status "failed" $false "DCS_updater.exe not found at: $updaterPath"
        exit 1
    }

    # ── Stop all DCS instances ────────────────────────────────────────────────
    Write-Status "stopping" $true "Stopping all DCS servers..."

    foreach ($inst in $instances) {
        # End the Task Scheduler task so its state clears from "Running"
        schtasks /end /tn $inst.service_name 2>$null | Out-Null

        # Kill the process directly by matching the saved_games_key in its command line
        $key  = $inst.saved_games_key
        $proc = Get-CimInstance Win32_Process -Filter "name='DCS_server.exe'" |
                Where-Object { $_.CommandLine -like "*$key*" }
        if ($proc) {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }

    # Give processes time to fully exit
    Start-Sleep -Seconds 10

    # ── Run DCS_updater.exe ───────────────────────────────────────────────────
    Write-Status "updating" $true "Running DCS updater — this may take 10-60 minutes..."

    $updater = Start-Process -FilePath $updaterPath `
                             -ArgumentList "update" `
                             -Wait -PassThru -NoNewWindow

    if ($updater.ExitCode -ne 0) {
        Write-Status "failed" $false "DCS_updater.exe failed with exit code $($updater.ExitCode)"
        exit 1
    }

    # ── Restart all DCS instances ─────────────────────────────────────────────
    Write-Status "restarting" $true "Restarting DCS servers..."

    foreach ($inst in $instances) {
        schtasks /run /tn $inst.service_name 2>$null | Out-Null
        Start-Sleep -Seconds 5
    }

    Write-Status "complete" $false "Update complete. Servers are coming back online."

} catch {
    Write-Status "failed" $false "Unexpected error: $_"
    exit 1
}
