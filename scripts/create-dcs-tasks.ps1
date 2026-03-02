$sid = (Get-LocalUser -Name $env:USERNAME).SID.Value
$dcsExe = "C:\Program Files\Eagle Dynamics\DCS World Server\bin\DCS_server.exe"

foreach ($server in @('SouthernBBQ', 'SmokeyBBQ', 'MemphisBBQ')) {
    $taskName = "DCS-$server"
    $xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.3" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <URI>\$taskName</URI>
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
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <IdleSettings>
      <Duration>PT10M</Duration>
      <WaitTimeout>PT1H</WaitTimeout>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
  </Settings>
  <Triggers />
  <Actions Context="Author">
    <Exec>
      <Command>$dcsExe</Command>
      <Arguments>-w $server</Arguments>
    </Exec>
  </Actions>
</Task>
"@
    $tmpFile = [System.IO.Path]::GetTempFileName() + ".xml"
    [System.IO.File]::WriteAllText($tmpFile, $xml, [System.Text.Encoding]::Unicode)
    schtasks /create /tn $taskName /xml $tmpFile /f
    Remove-Item $tmpFile
    Write-Host "Created task: $taskName"
}
