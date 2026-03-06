foreach ($k in @('SouthernBBQ','SmokeyBBQ','MemphisBBQ','TexasBBQ')) {
    $cfg = "C:\Users\DCSgoon\Saved Games\$k\Config\serverSettings.lua"
    Write-Host "=== $k ==="
    if (Test-Path $cfg) {
        Select-String -Path $cfg -Pattern 'port|webgui|["'']port' | Select-Object -ExpandProperty Line
    } else {
        Write-Host "(no serverSettings.lua)"
    }
}
