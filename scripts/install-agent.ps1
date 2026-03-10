#Requires -RunAsAdministrator
<#
.SYNOPSIS
    DCS Platform community host installer.

.DESCRIPTION
    Installs the DCS Agent, frp tunnel client, and configures your DCS World
    server instance to be managed via the DCS Platform Discord bot.

    No Tailscale or VPN required — the agent connects back to the orchestrator
    through an encrypted frp tunnel.

.PARAMETER InviteCode
    Your invite code (format: GOON-XXXX-XXXX-XXXX). Get this from the server admin.

.PARAMETER InstanceName
    A friendly name for your DCS server shown in Discord (default: "Community Server").

.PARAMETER ServiceName
    Windows Task Scheduler task name for your DCS instance (default: "DCS-community").
    Must be unique on this machine.

.PARAMETER InstallDir
    Where to install the DCS Agent (default: C:\DCSAgent).

.EXAMPLE
    .\install-agent.ps1 -InviteCode GOON-XXXX-XXXX-XXXX

.EXAMPLE
    .\install-agent.ps1 -InviteCode GOON-XXXX-XXXX-XXXX -InstanceName "MySquadron Server"
#>
[CmdletBinding(DefaultParameterSetName = "Install")]
param(
    [Parameter(Mandatory, ParameterSetName = "Install")]
    [string]$InviteCode,

    [Parameter(ParameterSetName = "Update")]
    [switch]$Update,

    [string]$OrchestratorUrl = "",

    [string]$AgentZipSha256 = "",

    [string]$HostName     = "",
    [string]$InstanceName = "Community Server",
    [string]$ServiceName  = "DCS-community",
    [string]$InstallDir   = "C:\DCSAgent"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference    = "SilentlyContinue"   # speeds up Invoke-WebRequest downloads

# ── Validate orchestrator URL ───────────────────────────────────────────────────

$OrchestratorUrl = $OrchestratorUrl.TrimEnd("/")
while (-not $OrchestratorUrl.StartsWith("https://")) {
    Write-Host ""
    Write-Host "  Orchestrator URL is required (e.g. https://goon.gsquad.cc)." -ForegroundColor Yellow
    $OrchestratorUrl = (Read-Host "  Enter orchestrator URL").Trim().TrimEnd("/")
}

# ── Constants ──────────────────────────────────────────────────────────────────

$ORCHESTRATOR  = $OrchestratorUrl
$FRPC_VERSION  = "0.61.0"
$FRPC_ZIP_URL  = "https://github.com/fatedier/frp/releases/download/v$FRPC_VERSION/frp_${FRPC_VERSION}_windows_amd64.zip"
$NSSM_ZIP_URL  = "$OrchestratorUrl/install/nssm.zip"

# ── Helpers ────────────────────────────────────────────────────────────────────

function Write-Step { param([string]$Msg) Write-Host "`n==> $Msg" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Msg) Write-Host "    OK: $Msg"    -ForegroundColor Green }
function Write-Warn { param([string]$Msg) Write-Host "    WARN: $Msg"  -ForegroundColor Yellow }
function Write-Fail { param([string]$Msg) Write-Host "    FAIL: $Msg"  -ForegroundColor Red }

function Get-OrchestratorError([System.Management.Automation.ErrorRecord]$Err) {
    try {
        $body = $Err.ErrorDetails.Message | ConvertFrom-Json
        if ($body.detail) { return $body.detail }
        if ($body.title)  { return $body.title }
    } catch { }
    return $Err.Exception.Message
}

function Download-File([string]$Url, [string]$Dest) {
    Write-Host "    Downloading $(Split-Path $Url -Leaf) ..." -ForegroundColor DarkGray
    Invoke-WebRequest -Uri $Url -OutFile $Dest -UseBasicParsing
}

function Get-Sha256([string]$Path) {
    return (Get-FileHash -Path $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Assert-Sha256([string]$Path, [string]$Expected) {
    $actual = Get-Sha256 $Path
    if ($actual -ne $Expected.ToLowerInvariant()) {
        throw "Hash mismatch for $(Split-Path $Path -Leaf).`n  Expected: $Expected`n  Actual:   $actual"
    }
    Write-Ok "Hash verified: $actual"
}

# ── Banner ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host "   DCS Platform  —  Community Host Installer" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Magenta

# ══════════════════════════════════════════════════════════════════════════════
# UPDATE MODE — patch agent source in-place and restart service
# ══════════════════════════════════════════════════════════════════════════════
if ($Update) {
    Write-Host " Mode        : UPDATE" -ForegroundColor Yellow
    Write-Host " Install dir : $InstallDir"
    Write-Host ""

    if (-not (Test-Path "$InstallDir\src")) {
        throw "Agent not found at $InstallDir — run without -Update to do a fresh install."
    }

    Write-Step "Downloading latest agent source"
    $agentZip = "$env:TEMP\dcs-agent-update.zip"
    Download-File "$ORCHESTRATOR/install/agent.zip" $agentZip
    if ($AgentZipSha256) { Assert-Sha256 $agentZip $AgentZipSha256 }

    Write-Step "Stopping DCSAgent service"
    Stop-Service DCSAgent -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2

    Write-Step "Extracting updated source"
    Expand-Archive -Path $agentZip -DestinationPath "$InstallDir\src" -Force
    Remove-Item $agentZip -ErrorAction SilentlyContinue

    Write-Step "Installing/updating Python dependencies"
    $pip = "$InstallDir\venv\Scripts\pip.exe"
    if (Test-Path $pip) {
        & $pip install --quiet --upgrade -r "$InstallDir\src\agent\requirements.txt"
        if ($LASTEXITCODE -ne 0) { throw "pip install failed (exit $LASTEXITCODE)" }
        Write-Ok "Dependencies updated"
    } else {
        Write-Warn "venv not found at $InstallDir\venv — skipping pip install"
    }

    # Copy helper scripts to install root (used by Task Scheduler tasks)
    $updateScriptSrc = "$InstallDir\src\agent\scripts\update_DCS_auto.ps1"
    if (Test-Path $updateScriptSrc) {
        Copy-Item $updateScriptSrc "$InstallDir\update_DCS_auto.ps1" -Force
        Write-Ok "update_DCS_auto.ps1 updated"
    }

    Write-Step "Starting DCSAgent service"
    Start-Service DCSAgent
    Write-Ok "DCSAgent restarted with updated source"

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "   Agent updated successfully!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    exit 0
}

# Prompt for a friendly host name if not passed as a parameter
if (-not $HostName) {
    Write-Host ""
    Write-Host "  What should this host be called in Discord?" -ForegroundColor Cyan
    Write-Host "  (e.g. 'DOC's Server', 'East Coast BBQ', 'MySquadron Host')" -ForegroundColor DarkGray
    $HostName = (Read-Host "  Host name").Trim()
    if (-not $HostName) { $HostName = $env:COMPUTERNAME }
}

# Prompt for the instance/server name if still the default
if ($InstanceName -eq "Community Server") {
    Write-Host ""
    Write-Host "  What is the name of your DCS server instance?" -ForegroundColor Cyan
    Write-Host "  (shown in Discord commands like /dcs start — e.g. 'MySquadron Server')" -ForegroundColor DarkGray
    $typed = (Read-Host "  Instance name").Trim()
    if ($typed) { $InstanceName = $typed }
}

Write-Host " Invite code : $InviteCode"
Write-Host " Host name   : $HostName"
Write-Host " Instance    : $InstanceName"
Write-Host " Service     : $ServiceName"
Write-Host " Install dir : $InstallDir"
Write-Host ""

# ══════════════════════════════════════════════════════════════════════════════
# 1. Detect DCS World Server installation
# ══════════════════════════════════════════════════════════════════════════════
Write-Step "Detecting DCS World Server installation"

$dcsSearchPaths = @(
    "C:\Program Files\Eagle Dynamics\DCS World OpenBeta Server\bin\DCS_server.exe",
    "C:\Program Files\Eagle Dynamics\DCS World Server\bin\DCS_server.exe",
    "D:\Program Files\Eagle Dynamics\DCS World OpenBeta Server\bin\DCS_server.exe",
    "D:\Program Files\Eagle Dynamics\DCS World Server\bin\DCS_server.exe",
    "E:\Program Files\Eagle Dynamics\DCS World OpenBeta Server\bin\DCS_server.exe",
    "E:\Program Files\Eagle Dynamics\DCS World Server\bin\DCS_server.exe"
)

$dcsExe = $null
foreach ($p in $dcsSearchPaths) {
    if (Test-Path $p) { $dcsExe = $p; break }
}

if (-not $dcsExe) {
    Write-Warn "DCS_server.exe not found in common locations."
    $dcsExe = Read-Host "  Enter full path to DCS_server.exe"
}
if (-not (Test-Path $dcsExe)) { throw "DCS_server.exe not found: $dcsExe" }
Write-Ok "DCS_server.exe: $dcsExe"

# ══════════════════════════════════════════════════════════════════════════════
# 2. Detect DCS Saved Games profile
# ══════════════════════════════════════════════════════════════════════════════
Write-Step "Locating DCS Saved Games server profile"

$savedGamesBase = "$env:USERPROFILE\Saved Games"
$dcsProfiles = @(Get-ChildItem $savedGamesBase -Directory -Filter "DCS*" -ErrorAction SilentlyContinue |
    Where-Object { Test-Path (Join-Path $_.FullName "Config\serverSettings.lua") })

$savedGamesKey  = $null
$savedGamesPath = $null

if ($dcsProfiles.Count -eq 1) {
    $savedGamesKey  = $dcsProfiles[0].Name
    $savedGamesPath = $dcsProfiles[0].FullName
    Write-Ok "Auto-detected: $savedGamesKey"
} elseif ($dcsProfiles.Count -gt 1) {
    Write-Host "  Multiple DCS server profiles found:"
    for ($i = 0; $i -lt $dcsProfiles.Count; $i++) {
        Write-Host "    [$i] $($dcsProfiles[$i].Name)"
    }
    $idx = [int](Read-Host "  Enter number to select")
    $savedGamesKey  = $dcsProfiles[$idx].Name
    $savedGamesPath = $dcsProfiles[$idx].FullName
} else {
    Write-Warn "No DCS server profiles found in $savedGamesBase."
    $savedGamesKey = Read-Host "  Enter the Saved Games key (e.g. DCS.openbeta_server)"
    $savedGamesPath = "$savedGamesBase\$savedGamesKey"
}

if (-not (Test-Path $savedGamesPath)) {
    throw "Saved Games path does not exist: $savedGamesPath"
}
Write-Ok "Profile: $savedGamesPath"

# ══════════════════════════════════════════════════════════════════════════════
# 3. Register with the orchestrator
# ══════════════════════════════════════════════════════════════════════════════
Write-Step "Registering with orchestrator"

$regBody = @{
    inviteCode = $InviteCode.Trim().ToUpper()
    hostName   = $HostName
    instances  = @(
        @{ serviceName = $ServiceName; name = $InstanceName }
    )
} | ConvertTo-Json -Depth 5

try {
    $reg = Invoke-RestMethod -Uri "$ORCHESTRATOR/api/v1/register" `
        -Method POST -Body $regBody -ContentType "application/json"
} catch {
    throw "Registration failed: $(Get-OrchestratorError $_)"
}

Write-Ok "Registered! Host ID   : $($reg.hostId)"
Write-Ok "            frp port  : $($reg.frpRemotePort)"
Write-Ok "            API key   : $($reg.agentApiKey.Substring(0,8))..."

# ══════════════════════════════════════════════════════════════════════════════
# 4. Create install directory structure
# ══════════════════════════════════════════════════════════════════════════════
Write-Step "Stopping existing services (if any)"

foreach ($svc in @("DCSAgent", "DCSAgentFrpc")) {
    if (Get-Service -Name $svc -ErrorAction SilentlyContinue) {
        Write-Warn "$svc is running — stopping before reinstall"
        try { Stop-Service $svc -Force 2>&1 | Out-Null } catch { }
        Start-Sleep -Seconds 1
    }
}

Write-Step "Creating install directory: $InstallDir"

foreach ($d in @($InstallDir, "$InstallDir\logs", "$InstallDir\src")) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

# ══════════════════════════════════════════════════════════════════════════════
# 5. Check / install Python 3.11+
# ══════════════════════════════════════════════════════════════════════════════
Write-Step "Checking Python 3.11+"

$pyCmd = $null
foreach ($candidate in @("python", "py", "python3")) {
    try {
        $v = & $candidate --version 2>&1
        if ($v -match "3\.(?:1[1-9]|[2-9]\d)") { $pyCmd = $candidate; break }
    } catch { }
}

if (-not $pyCmd) {
    # Try winget first; fall back to direct download if winget is unavailable
    $wingetOk = $false
    $wingetCmd = Get-Command winget -ErrorAction SilentlyContinue
    if ($wingetCmd) {
        Write-Warn "Python 3.11+ not found — installing via winget (this may take a minute)..."
        winget install --id Python.Python.3.11 -e `
            --accept-source-agreements --accept-package-agreements 2>&1 | Out-Null
        $wingetOk = ($LASTEXITCODE -eq 0)
    }

    if (-not $wingetOk) {
        Write-Warn "winget unavailable or failed — downloading Python 3.11 installer from python.org..."
        $pyInstaller = "$env:TEMP\python-3.11-amd64.exe"
        Download-File "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" $pyInstaller
        Start-Process -FilePath $pyInstaller `
            -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0" `
            -Wait
        Remove-Item $pyInstaller -ErrorAction SilentlyContinue
    }

    # Refresh PATH so the new python is visible in this session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
    $pyCmd = "python"
}
Write-Ok "Python: $(& $pyCmd --version 2>&1)"

# ══════════════════════════════════════════════════════════════════════════════
# 6. Download agent source from orchestrator
# ══════════════════════════════════════════════════════════════════════════════
Write-Step "Downloading DCS Agent"

$agentZip = "$env:TEMP\dcs-agent.zip"
Download-File "$ORCHESTRATOR/install/agent.zip" $agentZip
if ($AgentZipSha256) { Assert-Sha256 $agentZip $AgentZipSha256 }
Expand-Archive -Path $agentZip -DestinationPath "$InstallDir\src" -Force
Remove-Item $agentZip -ErrorAction SilentlyContinue
Write-Ok "Agent source extracted to $InstallDir\src"

# ══════════════════════════════════════════════════════════════════════════════
# 7. Create Python venv and install requirements
# ══════════════════════════════════════════════════════════════════════════════
Write-Step "Setting up Python virtual environment"

$venvDir  = "$InstallDir\venv"
$pip      = "$venvDir\Scripts\pip.exe"
$python   = "$venvDir\Scripts\python.exe"

& $pyCmd -m venv $venvDir
& $python -m pip install --quiet --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed (exit $LASTEXITCODE)" }
& $pip install -r "$InstallDir\src\agent\requirements.txt"
if ($LASTEXITCODE -ne 0) { throw "pip install requirements failed (exit $LASTEXITCODE)" }
Write-Ok "venv ready: $venvDir"

# ══════════════════════════════════════════════════════════════════════════════
# 8. Download frpc (frp client)
# ══════════════════════════════════════════════════════════════════════════════
Write-Step "Downloading frp client (frpc.exe)"

$frpcZip = "$env:TEMP\frpc.zip"
$frpcTmp = "$env:TEMP\frpc_extract"
Download-File $FRPC_ZIP_URL $frpcZip
Expand-Archive -Path $frpcZip -DestinationPath $frpcTmp -Force

$frpcSrc = Get-ChildItem "$frpcTmp\*\frpc.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $frpcSrc) { throw "frpc.exe not found in downloaded archive." }
Copy-Item $frpcSrc.FullName "$InstallDir\frpc.exe"
Remove-Item $frpcZip, $frpcTmp -Recurse -Force -ErrorAction SilentlyContinue
Write-Ok "frpc.exe ready"

# ══════════════════════════════════════════════════════════════════════════════
# 9. Download nssm (Non-Sucking Service Manager)
# ══════════════════════════════════════════════════════════════════════════════
Write-Step "Downloading nssm"

$nssmZip = "$env:TEMP\nssm.zip"
$nssmTmp = "$env:TEMP\nssm_extract"
Download-File $NSSM_ZIP_URL $nssmZip
Expand-Archive -Path $nssmZip -DestinationPath $nssmTmp -Force

$nssmSrc = Get-ChildItem "$nssmTmp\*\win64\nssm.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $nssmSrc) { throw "nssm.exe not found in downloaded archive." }
Copy-Item $nssmSrc.FullName "$InstallDir\nssm.exe"
Remove-Item $nssmZip, $nssmTmp -Recurse -Force -ErrorAction SilentlyContinue
Write-Ok "nssm.exe ready"

$nssm = "$InstallDir\nssm.exe"

# ══════════════════════════════════════════════════════════════════════════════
# 10. Write agent config.json
# ══════════════════════════════════════════════════════════════════════════════
Write-Step "Writing agent config.json"

$logPath           = "$savedGamesPath\Logs\dcs.log"
$missionsDir       = "$savedGamesPath\Missions"
$activeMissionsDir = "$savedGamesPath\Active Missions"

New-Item -ItemType Directory -Force -Path $activeMissionsDir | Out-Null
Write-Ok "Active Missions folder: $activeMissionsDir"

$agentCfg = [ordered]@{
    api_key             = $reg.agentApiKey
    host                = "0.0.0.0"
    port                = 8787
    nssm_path           = "$InstallDir\nssm.exe"
    log_dir             = "$InstallDir\logs"
    active_missions_dir = $activeMissionsDir
    orchestrator_url    = $ORCHESTRATOR
    host_id             = $reg.hostId
    instances = @(
        [ordered]@{
            name            = $InstanceName
            service_name    = $ServiceName
            exe_path        = $dcsExe
            saved_games_key = $savedGamesKey
            log_path        = $logPath
            missions_dir    = $missionsDir
            manager         = "task"
            auto_start      = $false
        }
    )
} | ConvertTo-Json -Depth 5

$agentCfgPath = "$InstallDir\config.json"
[System.IO.File]::WriteAllText($agentCfgPath, $agentCfg, [System.Text.UTF8Encoding]::new($false))
Write-Ok "config.json written"

# ══════════════════════════════════════════════════════════════════════════════
# 11. Write frpc.toml
# ══════════════════════════════════════════════════════════════════════════════
Write-Step "Writing frpc.toml"

$frpcToml = @"
serverAddr = "$($reg.frpServerAddr)"
serverPort = $($reg.frpServerPort)

[auth]
method = "token"
token = "$($reg.frpToken)"

[[proxies]]
name = "dcs-agent-$($reg.hostId)"
type = "tcp"
localIP = "127.0.0.1"
localPort = 8787
remotePort = $($reg.frpRemotePort)
"@

[System.IO.File]::WriteAllText("$InstallDir\frpc.toml", $frpcToml, [System.Text.UTF8Encoding]::new($false))
Write-Ok "frpc.toml written"

# ══════════════════════════════════════════════════════════════════════════════
# 12. Install DCSAgent Windows service (NSSM)
# ══════════════════════════════════════════════════════════════════════════════
Write-Step "Installing DCSAgent service"

# Remove existing service if present
$existing = Get-Service -Name "DCSAgent" -ErrorAction SilentlyContinue
if ($existing) {
    Write-Warn "DCSAgent service already exists — removing and reinstalling"
    try { & $nssm stop DCSAgent 2>&1 | Out-Null } catch { }
    try { & $nssm remove DCSAgent confirm 2>&1 | Out-Null } catch { }
    Start-Sleep -Seconds 1
}

& $nssm install DCSAgent $python
& $nssm set DCSAgent AppParameters "-m agent --config `"$agentCfgPath`" serve"
& $nssm set DCSAgent AppDirectory "$InstallDir\src"
& $nssm set DCSAgent Description "DCS World Agent API"
& $nssm set DCSAgent Start SERVICE_AUTO_START
& $nssm set DCSAgent AppStdout "$InstallDir\logs\agent.log"
& $nssm set DCSAgent AppStderr "$InstallDir\logs\agent.log"
& $nssm set DCSAgent AppRotateFiles 1
& $nssm set DCSAgent AppRotateSeconds 86400
Write-Ok "DCSAgent service installed"

# ══════════════════════════════════════════════════════════════════════════════
# 13. Install DCSAgentFrpc service (NSSM)
# ══════════════════════════════════════════════════════════════════════════════
Write-Step "Installing DCSAgentFrpc tunnel service"

$existingFrpc = Get-Service -Name "DCSAgentFrpc" -ErrorAction SilentlyContinue
if ($existingFrpc) {
    Write-Warn "DCSAgentFrpc service already exists — removing and reinstalling"
    try { & $nssm stop DCSAgentFrpc 2>&1 | Out-Null } catch { }
    try { & $nssm remove DCSAgentFrpc confirm 2>&1 | Out-Null } catch { }
    Start-Sleep -Seconds 1
}

& $nssm install DCSAgentFrpc "$InstallDir\frpc.exe"
& $nssm set DCSAgentFrpc AppParameters "-c `"$InstallDir\frpc.toml`""
& $nssm set DCSAgentFrpc AppDirectory "$InstallDir"
& $nssm set DCSAgentFrpc Description "DCS Agent frp reverse tunnel"
& $nssm set DCSAgentFrpc Start SERVICE_AUTO_START
& $nssm set DCSAgentFrpc AppStdout "$InstallDir\logs\frpc.log"
& $nssm set DCSAgentFrpc AppStderr "$InstallDir\logs\frpc.log"
Write-Ok "DCSAgentFrpc service installed"

# ══════════════════════════════════════════════════════════════════════════════
# 14. Create Task Scheduler task for DCS instance
#     (InteractiveToken so DCS can access the user's Saved Games session)
# ══════════════════════════════════════════════════════════════════════════════
Write-Step "Creating Task Scheduler task for DCS instance ($ServiceName)"

$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$sid         = $currentUser.User.Value
$dcsArgs     = "-w $savedGamesKey"
$dcsBinDir   = Split-Path $dcsExe -Parent

$taskXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.3" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <URI>\$ServiceName</URI>
  </RegistrationInfo>
  <Principals>
    <Principal id="Author">
      <UserId>$sid</UserId>
      <LogonType>InteractiveToken</LogonType>
    </Principal>
  </Principals>
  <Settings>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
  </Settings>
  <Triggers />
  <Actions Context="Author">
    <Exec>
      <Command>$dcsExe</Command>
      <Arguments>$dcsArgs</Arguments>
      <WorkingDirectory>$dcsBinDir</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

$tmpXml = [System.IO.Path]::GetTempFileName() + ".xml"
[System.IO.File]::WriteAllText($tmpXml, $taskXml, [System.Text.Encoding]::Unicode)

# Remove existing task if present
try { schtasks /delete /tn $ServiceName /f 2>&1 | Out-Null } catch { }

schtasks /create /tn $ServiceName /xml $tmpXml /f | Out-Null
Remove-Item $tmpXml -ErrorAction SilentlyContinue
Write-Ok "Task Scheduler task created: $ServiceName"

# ══════════════════════════════════════════════════════════════════════════════
# 15. Create DCS-UpdateDCS Task Scheduler task (runs as SYSTEM)
# ══════════════════════════════════════════════════════════════════════════════
Write-Step "Creating DCS-UpdateDCS update task"

# Copy the update script into the install directory
$updateScript = "$InstallDir\update_DCS_auto.ps1"
$updateScriptSrc = "$InstallDir\src\agent\scripts\update_DCS_auto.ps1"
if (Test-Path $updateScriptSrc) {
    Copy-Item $updateScriptSrc $updateScript -Force
} else {
    Write-Warn "update_DCS_auto.ps1 not found in agent source — update task will not work."
}

$updateTaskXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.3" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <URI>\DCS-UpdateDCS</URI>
    <Description>Stops DCS servers, runs DCS_updater.exe, restarts servers. Triggered by DCS Agent.</Description>
  </RegistrationInfo>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-18</UserId>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
  </Settings>
  <Triggers />
  <Actions Context="Author">
    <Exec>
      <Command>powershell.exe</Command>
      <Arguments>-NoProfile -ExecutionPolicy Bypass -File "$updateScript" -ConfigFile "$agentCfgPath"</Arguments>
    </Exec>
  </Actions>
</Task>
"@

$tmpUpdateXml = [System.IO.Path]::GetTempFileName() + ".xml"
[System.IO.File]::WriteAllText($tmpUpdateXml, $updateTaskXml, [System.Text.Encoding]::Unicode)
try { schtasks /delete /tn "DCS-UpdateDCS" /f 2>&1 | Out-Null } catch { }
schtasks /create /tn "DCS-UpdateDCS" /xml $tmpUpdateXml /f | Out-Null
Remove-Item $tmpUpdateXml -ErrorAction SilentlyContinue
Write-Ok "DCS-UpdateDCS task created (runs as SYSTEM)"

# Ensure ProgramData status directory exists and is writable by SYSTEM
New-Item -ItemType Directory -Force -Path "C:\ProgramData\DCSAgent" | Out-Null
Write-Ok "C:\ProgramData\DCSAgent created"

# ══════════════════════════════════════════════════════════════════════════════
# 16. Install DCS Lua status hook
# ══════════════════════════════════════════════════════════════════════════════
Write-Step "Installing DCS Lua status hook"

$hooksDir = "$savedGamesPath\Scripts\Hooks"
New-Item -ItemType Directory -Force -Path $hooksDir | Out-Null

$hookSrc = "$InstallDir\src\agent\scripts\dcs_agent_hook.lua"
if (Test-Path $hookSrc) {
    Copy-Item $hookSrc "$hooksDir\dcs_agent_hook.lua" -Force
    Write-Ok "Hook installed to $hooksDir"
} else {
    Write-Warn "Hook script not found at $hookSrc — skipping. Mission/player status will not be available."
}

# ══════════════════════════════════════════════════════════════════════════════
# 17. Start services
# ══════════════════════════════════════════════════════════════════════════════
Write-Step "Starting services"

try {
    Start-Service DCSAgentFrpc
    Write-Ok "DCSAgentFrpc started (tunnel connecting to $($reg.frpServerAddr):$($reg.frpServerPort))"
} catch {
    Write-Warn "DCSAgentFrpc failed to start — check log: $InstallDir\logs\frpc.log"
}

Start-Sleep -Seconds 2

try {
    Start-Service DCSAgent
    Write-Ok "DCSAgent started (listening on port 8787)"
} catch {
    Write-Warn "DCSAgent failed to start — check log: $InstallDir\logs\agent.log"
    Write-Host ""
    Write-Host "  Last 20 lines of agent log:" -ForegroundColor Yellow
    if (Test-Path "$InstallDir\logs\agent.log") {
        Get-Content "$InstallDir\logs\agent.log" -Tail 20 | ForEach-Object { Write-Host "    $_" }
    } else {
        Write-Host "    (log file not found — service may have failed before writing output)" -ForegroundColor DarkGray
    }
}

# ══════════════════════════════════════════════════════════════════════════════
# 18. Create desktop shortcuts (optional)
# ══════════════════════════════════════════════════════════════════════════════
Write-Step "Desktop shortcuts"
$createShortcuts = Read-Host "  Create desktop shortcuts for starting and updating? [Y/n]"
if ($createShortcuts -eq "" -or $createShortcuts -match "^[Yy]") {
    $desktop  = [System.Environment]::GetFolderPath("Desktop")
    $wsh      = New-Object -ComObject WScript.Shell
    $dcsIco   = "$env:SystemDrive\Program Files\Eagle Dynamics\DCS World Server\FUI\DCS-3.ico"

    # ── Remove the default DCS World Server shortcut placed by the installer ──
    foreach ($name in @("DCS World Server", "DCS World OpenBeta Server")) {
        $lnk = "$desktop\$name.lnk"
        if (Test-Path $lnk) {
            Remove-Item $lnk -Force
            Write-Ok "Removed default shortcut: $name.lnk"
        }
    }

    # ── Start <InstanceName> ──────────────────────────────────────────────────
    $startLnkPath = "$desktop\Start $InstanceName.lnk"
    $startLnk = $wsh.CreateShortcut($startLnkPath)
    $startLnk.TargetPath  = "cmd.exe"
    $startLnk.Arguments   = "/c schtasks /run /tn `"$ServiceName`""
    $startLnk.WindowStyle = 7  # minimised — no console flash
    $startLnk.Description = "Start $InstanceName via Task Scheduler (bot-managed)"
    if (Test-Path $dcsIco) { $startLnk.IconLocation = "$dcsIco,0" }
    $startLnk.Save()
    Write-Ok "Created: Start $InstanceName.lnk"

    # ── Update DCS Agent ──────────────────────────────────────────────────────
    # Write a small helper script so the shortcut target stays simple and the
    # orchestrator URL is remembered automatically after install.
    $updateHelper = "$InstallDir\update-agent.ps1"
    $updateHelperContent = @"
#Requires -RunAsAdministrator
# Auto-generated by installer. Downloads and runs the latest agent in update mode.
`$f = "`$env:TEMP\install-agent.ps1"
Invoke-WebRequest -UseBasicParsing $OrchestratorUrl/install/install.ps1 -OutFile `$f
& powershell -ExecutionPolicy Bypass -File `$f -Update -OrchestratorUrl $OrchestratorUrl
"@
    [System.IO.File]::WriteAllText($updateHelper, $updateHelperContent, [System.Text.UTF8Encoding]::new($false))

    $updateLnkPath = "$desktop\Update DCS Agent.lnk"
    $updateLnk = $wsh.CreateShortcut($updateLnkPath)
    $updateLnk.TargetPath  = "powershell.exe"
    $updateLnk.Arguments   = "-NoProfile -ExecutionPolicy Bypass -File `"$updateHelper`""
    $updateLnk.WindowStyle = 1
    $updateLnk.Description = "Update DCS Agent to the latest version"
    if (Test-Path $dcsIco) { $updateLnk.IconLocation = "$dcsIco,0" }
    $updateLnk.Save()
    # Set the Run as Administrator flag (byte 0x15, bit 0x20 of the .lnk header)
    $lnkBytes = [System.IO.File]::ReadAllBytes($updateLnkPath)
    $lnkBytes[0x15] = $lnkBytes[0x15] -bor 0x20
    [System.IO.File]::WriteAllBytes($updateLnkPath, $lnkBytes)
    Write-Ok "Created: Update DCS Agent.lnk (runs as administrator)"
}

# ══════════════════════════════════════════════════════════════════════════════
# Done
# ══════════════════════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   Community host installed successfully!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Host ID      : $($reg.hostId)" -ForegroundColor White
Write-Host "  Host name    : $InstanceName"  -ForegroundColor White
Write-Host "  frp port     : $($reg.frpRemotePort)" -ForegroundColor White
Write-Host "  Install dir  : $InstallDir"    -ForegroundColor White
Write-Host ""
Write-Host "  Your DCS server is now registered and the tunnel is active." -ForegroundColor Yellow
Write-Host "  The server admin can manage your instance from Discord." -ForegroundColor Yellow
Write-Host ""
Write-Host "  To start your DCS server:  /dcs start (via Discord)" -ForegroundColor Cyan
Write-Host "  Services:  DCSAgent, DCSAgentFrpc (auto-start on Windows boot)" -ForegroundColor Cyan
Write-Host ""
Write-Host "  NOTE: Restart DCS after install so the Lua hook activates." -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Green
