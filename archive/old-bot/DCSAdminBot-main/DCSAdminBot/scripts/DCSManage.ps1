param (
    [string]$Action = "start",
    [string]$Target = "all"
)

$BasePath = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ConfigPath = Join-Path $BasePath "..\config\servers.json"
$LogFile = Join-Path $BasePath "..\Logs\restart_log.txt"

if (-not (Test-Path $ConfigPath) -or -not (Test-Path $ConfigJsonPath)) {
    Write-Output "❌ Missing configuration files."
    exit 1
}

$servers = (Get-Content $ConfigPath | ConvertFrom-Json).instances


function Write-Log {
    param ([string]$Action, [string]$Target)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "[$timestamp] [$Action] $Target"
}

function Send-DiscordAlert {
    param (
        [string]$Message
    )
    Write-Output $Message
    Write-Log "alert_message" $Message
}

function Sanitize-MissionScripting {
    foreach ($key in $servers.PSObject.Properties.Name) {
        $SavedGamesPath = "$env:USERPROFILE\Saved Games\$($servers.$key.name)\Scripts\MissionScripting.lua"
        if (Test-Path $SavedGamesPath) {
            $lines = Get-Content $SavedGamesPath
            $output = @()
            foreach ($line in $lines) {
                if ($line -match '^\s*sanitizeModule\(' -and $line -notmatch '^\s*--') {
                    $output += '--' + $line
                } else {
                    $output += $line
                }
            }
            $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            $output += "-- Last sanitized: $timestamp"
            $output | Set-Content $SavedGamesPath -Force
            Write-Log "sanitized" $SavedGamesPath
        }
    }
}

function Minimize-DCSWindows {
    Start-Sleep -Seconds 10
    Add-Type @"
        using System;
        using System.Runtime.InteropServices;
        public class WinAPI {
            [DllImport("user32.dll")]
            public static extern int ShowWindow(IntPtr hWnd, int nCmdShow);
        }
"@
    $DCSProcesses = Get-Process -Name "DCS_server" -ErrorAction SilentlyContinue
    foreach ($proc in $DCSProcesses) {
        $hWnd = $proc.MainWindowHandle
        if ($hWnd -ne [IntPtr]::Zero) {
            [WinAPI]::ShowWindow($hWnd, 6)
            Write-Log "minimized" $proc.Id
        }
    }
}

function Start-SingleDCS {
    param ([string]$key)
    $name = $servers.$key.name
    $exe = $servers.$key.exe
    if (-not (Test-Path $exe)) {
        Write-Log "exe_not_found" $exe
        return
    }
    try {
		Sanitize-MissionScripting
        Start-Process -FilePath $exe -ArgumentList "-w $name" -PassThru | Out-Null
        Start-Sleep -Seconds 5
        Minimize-DCSWindows
        Write-Log "started" $name
        Write-Output "STARTED $name"
    } catch {
        Write-Log "start_failed" $_
        Write-Output "FAILED_START $name"
    }
}

function Stop-SingleDCS {
    param ([string]$key)
    $name = $servers.$key.name
    try {
        $processes = Get-CimInstance Win32_Process | Where-Object {
            $_.Name -eq "DCS_server.exe" -and $_.CommandLine -match "-w $name"
        }
        if ($processes) {
            $processes | ForEach-Object {
                Stop-Process -Id $_.ProcessId -Force | Out-Null
                Write-Log "stopped" $name
                Write-Output "STOPPED $name"
            }
        } else {
            Write-Log "not_running" $name
            Write-Output "NOT_RUNNING $name"
        }
    } catch {
        Write-Log "stop_failed" $_
        Write-Output "FAILED_STOP $name"
    }
}

function Restart-DCS {
    param ([string]$target = "all")
    $targets = @()
    if ($target -eq "all") {
        $targets = $servers.PSObject.Properties.Name
    } else {
        $matchedKey = $servers.PSObject.Properties.Name | Where-Object { $servers.$_.name -eq $target }
        if (-not $matchedKey) {
            Write-Log "invalid_restart_target" $target
            Write-Output "INVALID_TARGET $target"
            return
        }
        $targets += $matchedKey
    }

    foreach ($key in $targets) {
        Stop-SingleDCS $key
        Start-Sleep -Seconds 5
        Start-SingleDCS $key
    }
}

switch ($Action.ToLower()) {
    "start"   {
        if ($Target -eq "all") {
            foreach ($key in $servers.PSObject.Properties.Name) { Start-SingleDCS $key }
        } else {
            $matchedKey = $servers.PSObject.Properties.Name | Where-Object { $servers.$_.name -eq $Target }
            if ($matchedKey) { Start-SingleDCS $matchedKey } else {
                Write-Log "invalid_start_target" $Target
                Send-DiscordAlert "❌ Invalid instance name: $Target"
            }
        }
        Sanitize-MissionScripting
    }
    "stop"    {
        if ($Target -eq "all") {
            foreach ($key in $servers.PSObject.Properties.Name) { Stop-SingleDCS $key }
        } else {
            $matchedKey = $servers.PSObject.Properties.Name | Where-Object { $servers.$_.name -eq $Target }
            if ($matchedKey) { Stop-SingleDCS $matchedKey } else {
                Write-Log "invalid_stop_target" $Target
                Send-DiscordAlert "❌ Invalid instance name: $Target"
            }
        }
    }
    "restart" { Restart-DCS $Target }
    default   { Write-Log "unknown_action" $Action; exit 1 }
}
