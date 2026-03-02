$js = Get-Content "C:\Program Files\Eagle Dynamics\DCS World Server\WebGUI\js\app.js" -Raw
# Find all quoted strings that look like URL paths
$matches = [regex]::Matches($js, '"(/[a-zA-Z0-9/_\-\.]{3,60})"')
$paths = $matches | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
$paths | Where-Object { $_ -match '^/[a-z]' -and $_ -notmatch '\.(js|css|png|woff|map)' }
