#Requires -RunAsAdministrator
<#
.SYNOPSIS
    DCS Platform community host uninstaller.

.DESCRIPTION
    Stops and removes the DCSAgent and DCSAgentFrpc services, deletes the
    Task Scheduler DCS task, removes the Lua hook, and deletes the install
    directory.

.PARAMETER InstallDir
    Where the DCS Agent was installed (default: C:\DCSAgent).

.PARAMETER ServiceName
    Windows Task Scheduler task name for the DCS instance (default: DCS-community).

.EXAMPLE
    .\uninstall-agent.ps1

.EXAMPLE
    .\uninstall-agent.ps1 -InstallDir C:\DCSAgent -ServiceName DCS-community
#>
param(
    [string]$InstallDir   = "C:\DCSAgent",
    [string]$ServiceName  = "DCS-community"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step { param([string]$Msg) Write-Host "`n==> $Msg" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Msg) Write-Host "    OK: $Msg"   -ForegroundColor Green }
function Write-Warn { param([string]$Msg) Write-Host "    WARN: $Msg" -ForegroundColor Yellow }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host "   DCS Platform  -  Community Host Uninstaller" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "  Install dir  : $InstallDir"
Write-Host "  DCS task     : $ServiceName"
Write-Host ""

$confirm = Read-Host "  This will remove the DCS Agent from this machine. Continue? [y/N]"
if ($confirm -notmatch "^[Yy]") {
    Write-Host "  Aborted." -ForegroundColor Yellow
    exit 0
}

# ── 1. Stop and remove NSSM services ──────────────────────────────────────────

Write-Step "Stopping and removing DCS Agent services"

$nssm = "$InstallDir\nssm.exe"

foreach ($svc in @("DCSAgent", "DCSAgentFrpc")) {
    if (Get-Service -Name $svc -ErrorAction SilentlyContinue) {
        if (Test-Path $nssm) {
            try { & $nssm stop $svc 2>&1 | Out-Null } catch { }
            Start-Sleep -Seconds 1
            try { & $nssm remove $svc confirm 2>&1 | Out-Null } catch { }
            Write-Ok "$svc removed"
        } else {
            try { Stop-Service $svc -Force 2>&1 | Out-Null } catch { }
            try { sc.exe delete $svc 2>&1 | Out-Null } catch { }
            Write-Ok "$svc stopped and deleted via sc.exe"
        }
    } else {
        Write-Warn "$svc not found — skipping"
    }
}

# ── 2. Remove Task Scheduler tasks ────────────────────────────────────────────

Write-Step "Removing Task Scheduler tasks"

try { schtasks /delete /tn $ServiceName /f 2>&1 | Out-Null } catch { }
Write-Ok "Task '$ServiceName' removed (if it existed)"

try { schtasks /delete /tn "DCS-UpdateDCS" /f 2>&1 | Out-Null } catch { }
Write-Ok "Task 'DCS-UpdateDCS' removed (if it existed)"

# ── 3. Remove Lua hook from all DCS Saved Games profiles ──────────────────────

Write-Step "Removing DCS Lua hook"

$savedGamesBase = "$env:USERPROFILE\Saved Games"
$hooked = 0
Get-ChildItem $savedGamesBase -Directory -Filter "DCS*" -ErrorAction SilentlyContinue | ForEach-Object {
    $hookPath = "$($_.FullName)\Scripts\Hooks\dcs_agent_hook.lua"
    if (Test-Path $hookPath) {
        Remove-Item $hookPath -Force
        Write-Ok "Removed hook from $($_.Name)"
        $hooked++
    }
}
if ($hooked -eq 0) { Write-Warn "No hook files found" }

# ── 4. Delete install directory ───────────────────────────────────────────────

Write-Step "Deleting install directory: $InstallDir"

if (Test-Path $InstallDir) {
    Remove-Item $InstallDir -Recurse -Force
    Write-Ok "Deleted $InstallDir"
} else {
    Write-Warn "$InstallDir not found — already removed?"
}

# ── Done ──────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   DCS Agent uninstalled." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  NOTE: Your DCS Saved Games profile and missions are untouched." -ForegroundColor Yellow
Write-Host "  To fully remove the host from Discord, ask an admin to run /dcs remove-host." -ForegroundColor Yellow
Write-Host ""
