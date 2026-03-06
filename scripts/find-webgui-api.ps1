$js = "C:\Program Files\Eagle Dynamics\DCS World Server\WebGUI\js\app.js"
$patterns = @('fetch\(', '\.get\(', '\.post\(', '/server', '/player', '/mission', '/coalition', '/unit', 'api/')
foreach ($pat in $patterns) {
    $hits = Select-String -Path $js -Pattern $pat | Select-Object -First 5
    foreach ($h in $hits) {
        Write-Host $h.Line.Trim().Substring(0, [Math]::Min(150, $h.Line.Trim().Length))
    }
}
