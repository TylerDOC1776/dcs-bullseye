$sid = (Get-LocalUser -Name $env:USERNAME).SID.Value
$script = "C:\dcs-platform\minimize-dcs-windows.ps1"

$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.3" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <URI>\DCS-MinimizeWindows</URI>
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
    <ExecutionTimeLimit>PT1M</ExecutionTimeLimit>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
  </Settings>
  <Triggers />
  <Actions Context="Author">
    <Exec>
      <Command>powershell.exe</Command>
      <Arguments>-NoProfile -WindowStyle Hidden -File "$script"</Arguments>
    </Exec>
  </Actions>
</Task>
"@

$tmpFile = [System.IO.Path]::GetTempFileName() + ".xml"
[System.IO.File]::WriteAllText($tmpFile, $xml, [System.Text.Encoding]::Unicode)
schtasks /create /tn "DCS-MinimizeWindows" /xml $tmpFile /f
Remove-Item $tmpFile
Write-Host "Created DCS-MinimizeWindows task"
