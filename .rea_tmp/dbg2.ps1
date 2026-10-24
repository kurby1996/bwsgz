param([string]$MsiPath)
$ErrorActionPreference = 'Stop'
function Invoke-MsiViewAll([string]$Sql) {
    $installer = New-Object -ComObject WindowsInstaller.Installer
    $db = $installer.GetType().InvokeMember('OpenDatabase','InvokeMethod',$null,$installer,@($MsiPath, 0))
    $view = $db.GetType().InvokeMember('OpenView','InvokeMethod',$null,$db,@($Sql))
    $view.GetType().InvokeMember('Execute','InvokeMethod',$null,$view,$null)
    $rows = @()
    while ($true) {
        $rec = $view.GetType().InvokeMember('Fetch','InvokeMethod',$null,$view,$null)
        if ($null -eq $rec) { break }
        $colCount = [int]$rec.GetType().InvokeMember('FieldCount','GetProperty',$null,$rec,$null)
        $vals = @()
        for ($i = 1; $i -le $colCount; $i++) {
            $vals += [string]$rec.GetType().InvokeMember('StringData','GetProperty',$null,$rec,$i)
        }
        $rows += ,($vals)
    }
    $view.GetType().InvokeMember('Close','InvokeMethod',$null,$view,$null)
    [Runtime.InteropServices.Marshal]::ReleaseComObject($view) | Out-Null
    [Runtime.InteropServices.Marshal]::ReleaseComObject($db) | Out-Null
    return ,$rows
}
$dirs = Invoke-MsiViewAll 'SELECT * FROM `Directory`'
Write-Output ("dirs count=" + $dirs.Count)
$nulls = 0
foreach ($r in $dirs) { if ($null -eq $r) { $nulls++ } }
Write-Output ("null elements=" + $nulls)
Write-Output ("first=" + $dirs[0][0] + " | last=" + $dirs[90][0])
