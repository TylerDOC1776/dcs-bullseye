# update_DCS_auto.ps1
# Headless DCS update — triggered by the DCS Agent via Task Scheduler.
# Runs as SYSTEM (no UAC prompt needed). Does NOT require user interaction.
# Progress written to C:\ProgramData\DCSAgent\update_status.json for the agent to poll.

$DCS_Updater_Path  = "C:\Program Files\Eagle Dynamics\DCS World Server\bin\DCS_updater.exe"
$DCS_Server_Exe    = "C:\Program Files\Eagle Dynamics\DCS World Server\bin\DCS_server.exe"
$MissionScript_Src = "C:\dcs-platform\MissionScripting.lua"
$MissionScript_Dst = "C:\Program Files\Eagle Dynamics\DCS World Server\Scripts\MissionScripting.lua"
$StatusFile        = "C:\ProgramData\DCSAgent\update_status.json"
$LogFile           = "C:\ProgramData\DCSAgent\logs\dcs_update.log"

function Write-Status {
    param([string]$Phase, [string]$Message, [bool]$Running = $true)
    $obj = [PSCustomObject]@{
        phase     = $Phase
        message   = $Message
        running   = $Running
        timestamp = (Get-Date -Format "o")
    }
    $obj | ConvertTo-Json -Compress | Set-Content -Path $StatusFile -Force -Encoding UTF8
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [$Phase] $Message"
    Add-Content -Path $LogFile -Value $line -Force
    Write-Host $line
}

# ---- Stop all DCS server processes ----------------------------------------

Write-Status "stopping" "Stopping all DCS server instances..."
Stop-Process -Name "DCS_server" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 5
Write-Status "stopping" "All DCS servers stopped."

# ---- Run the DCS updater non-interactively ----------------------------------

Write-Status "updating" "Launching DCS_updater.exe update..."

$process = Start-Process -FilePath $DCS_Updater_Path `
    -ArgumentList "--quiet", "update" `
    -WindowStyle Hidden `
    -PassThru

$timeout = 3600   # 60 minutes max
$elapsed = 0
$interval = 15

while (-not $process.HasExited -and $elapsed -lt $timeout) {
    Start-Sleep -Seconds $interval
    $elapsed += $interval
    Write-Status "updating" "Updater running... ($elapsed s elapsed)"
}

if (-not $process.HasExited) {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    Write-Status "failed" "Updater timed out after $timeout seconds." $false
    exit 1
}

if ($process.ExitCode -ne 0) {
    Write-Status "failed" "Updater exited with code $($process.ExitCode)." $false
    exit 1
}

Write-Status "updating" "DCS Updater finished (exit code 0)."

# ---- Re-apply custom MissionScripting.lua -----------------------------------

Write-Status "patching" "Applying custom MissionScripting.lua..."
if (Test-Path $MissionScript_Src) {
    Copy-Item -Path $MissionScript_Dst -Destination "$MissionScript_Dst.bak" -Force -ErrorAction SilentlyContinue
    Copy-Item -Path $MissionScript_Src -Destination $MissionScript_Dst -Force
    Write-Status "patching" "MissionScripting.lua applied successfully."
} else {
    Write-Status "patching" "WARNING: Source MissionScripting.lua not found at $MissionScript_Src — skipped."
}

# ---- Start the three main DCS servers via Task Scheduler --------------------

Write-Status "starting" "Starting DCS servers via Task Scheduler..."
foreach ($task in @("DCS-SouthernBBQ", "DCS-SmokeyBBQ", "DCS-MemphisBBQ")) {
    $r = schtasks /run /tn $task 2>&1
    Write-Status "starting" "${task}: $r"
    Start-Sleep -Seconds 2
}

Write-Status "done" "DCS update complete. Servers are starting up." $false
