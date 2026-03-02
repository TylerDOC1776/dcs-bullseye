$hook_src = "$PSScriptRoot\dcs_agent_hook.lua"
$servers  = @('SouthernBBQ', 'SmokeyBBQ', 'MemphisBBQ', 'TexasBBQ')
$base     = "C:\Users\DCSgoon\Saved Games"

foreach ($s in $servers) {
    $hooks_dir = "$base\$s\Scripts\Hooks"
    New-Item -ItemType Directory -Force -Path $hooks_dir | Out-Null
    Copy-Item $hook_src "$hooks_dir\dcs_agent_hook.lua" -Force
    Write-Host "Installed hook for $s"
}
