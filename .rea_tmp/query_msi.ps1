param([string]$MsiPath)
$ErrorActionPreference = 'Stop'
$installer = New-Object -ComObject WindowsInstaller.Installer

function Invoke-MsiView([string]$Sql) {
    $db = $installer.GetType().InvokeMember('OpenDatabase','InvokeMethod',$null,$installer,@($MsiPath, 0))
    $view = $db.GetType().InvokeMember('OpenView','InvokeMethod',$null,$db,@($Sql))
    $view.GetType().InvokeMember('Execute','InvokeMethod',$null,$view,$null)
    $rows = @()
    while ($true) {
        $rec = $view.GetType().InvokeMember('Fetch','InvokeMethod',$null,$view,$null)
        if ($null -eq $rec) { break }
        $colCount = $rec.GetType().InvokeMember('FieldCount','GetProperty',$null,$rec,$null)
        $vals = @()
        for ($i = 1; $i -le $colCount; $i++) {
            $vals += [string]$rec.GetType().InvokeMember('StringData','GetProperty',$null,$rec,$i)
        }
        $rows += ,($vals -join "`t")
    }
    $view.GetType().InvokeMember('Close','InvokeMethod',$null,$view,$null)
    [Runtime.InteropServices.Marshal]::ReleaseComObject($view) | Out-Null
    [Runtime.InteropServices.Marshal]::ReleaseComObject($db) | Out-Null
    return $rows
}

Write-Output '=== PROPERTY ==='
Invoke-MsiView 'SELECT `Property`, `Value` FROM `Property`'

Write-Output ''
Write-Output '=== SUMMARYINFO ==='
$si = $installer.GetType().InvokeMember('SummaryInformation','GetProperty',$null,$installer,@($MsiPath, 0))
foreach ($pid_ in @(1,2,3,4,6,7,8,9,12,13,14,15,18,19)) {
    $val = $si.GetType().InvokeMember('Property','GetProperty',$null,$si,$pid_)
    Write-Output ("PID ${pid_}: $val")
}
