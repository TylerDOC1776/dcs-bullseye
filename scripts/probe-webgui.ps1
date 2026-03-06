$port = 8088
$paths = @(
    "/", "/v1", "/api", "/server", "/info", "/status", "/mission",
    "/missions", "/players", "/game", "/monitor", "/realtimemonitor",
    "/loggingws", "/auth", "/configuration"
)
foreach ($p in $paths) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:$port$p" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        Write-Host "$p => $($r.StatusCode): $($r.Content.Substring(0, [Math]::Min(120, $r.Content.Length)))"
    } catch {
        Write-Host "$p => ERROR: $($_.Exception.Message)"
    }
}
