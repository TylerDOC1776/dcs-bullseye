Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class Win32Gui {
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@

$minimized = 0
Get-Process DCS_server -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero } | ForEach-Object {
    [Win32Gui]::ShowWindow($_.MainWindowHandle, 6) | Out-Null  # 6 = SW_MINIMIZE
    $minimized++
}
Write-Host "Minimized $minimized DCS window(s)"
