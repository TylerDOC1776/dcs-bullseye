#Requires -Version 5.1
<#
.SYNOPSIS
    Run all test suites for the DCS platform.

.DESCRIPTION
    Runs pytest for agent/ and orchestrator/ in sequence.
    Exits with a non-zero code if any suite fails.

.PARAMETER Package
    Limit to a specific package: "agent" or "orchestrator".
    Defaults to running both.

.PARAMETER Verbose
    Pass -v to pytest for verbose output.

.EXAMPLE
    .\scripts\test.ps1
    .\scripts\test.ps1 -Package agent -Verbose
#>

param(
    [ValidateSet("agent", "orchestrator", "all")]
    [string]$Package = "all",
    [switch]$Verbose
)

$Root = Resolve-Path "$PSScriptRoot\.."
$PytestArgs = if ($Verbose) { @("-v") } else { @() }
$Failed = @()

function Invoke-Tests {
    param([string]$Name, [string]$Dir)
    Write-Host "`n=== $Name ===" -ForegroundColor Cyan
    Push-Location $Dir
    try {
        python -m pytest tests/ @PytestArgs
        if ($LASTEXITCODE -ne 0) { $script:Failed += $Name }
    } finally {
        Pop-Location
    }
}

if ($Package -eq "all" -or $Package -eq "agent") {
    Invoke-Tests -Name "agent" -Dir "$Root\agent"
}

if ($Package -eq "all" -or $Package -eq "orchestrator") {
    Invoke-Tests -Name "orchestrator" -Dir "$Root\orchestrator"
}

Write-Host ""
if ($Failed.Count -gt 0) {
    Write-Host "FAILED: $($Failed -join ', ')" -ForegroundColor Red
    exit 1
} else {
    Write-Host "All tests passed." -ForegroundColor Green
    exit 0
}
