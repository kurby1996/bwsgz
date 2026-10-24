param([string]$MsiPath)
$ErrorActionPreference = 'Stop'
$installer = New-Object -ComObject WindowsInstaller.Installer
$db = $installer.GetType().InvokeMember('OpenDatabase','InvokeMethod',$null,$installer,@($MsiPath, 0))
$view = $db.GetType().InvokeMember('OpenView','InvokeMethod',$null,$db,@('SELECT * FROM `Directory`'))
$view.GetType().InvokeMember('Execute','InvokeMethod',$null,$view,$null)
$rows = @()
while ($true) {
    $rec = $view.GetType().InvokeMember('Fetch','InvokeMethod',$null,$view,$null)
    if ($null -eq $rec) { break }
    $colCount = [int]$rec.GetType().InvokeMember('FieldCount','GetProperty',$null,$rec,$null)
    Write-Output ("row colcount=" + $colCount)
    $vals = @()
    for ($i = 1; $i -le $colCount; $i++) {
        $vals += [string]$rec.GetType().InvokeMember('StringData','GetProperty',$null,$rec,$i)
    }
    $rows += ,($vals)
}
Write-Output ("rows count=" + $rows.Count)
Write-Output ("first row type=" + $rows[0].GetType().FullName + " elem0=" + $rows[0][0])
