param([string]$MsiPath)
$ErrorActionPreference = 'Stop'
$installer = New-Object -ComObject WindowsInstaller.Installer

function Invoke-MsiViewAll([string]$Sql) {
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
$dirMap = @{}
foreach ($r in $dirs) { $dirMap[$r[0]] = $r[2] }
function Resolve-Dir([string]$d) {
    $parts = @()
    $cur = $d
    while ($cur -and $dirMap.ContainsKey($cur)) {
        $name = $dirMap[$cur] -split '\|' | Select-Object -Last 1
        $parts = @($name) + $parts
        $cur = ($dirs | Where-Object { $_[0] -eq $cur })[1]
    }
    return ($parts -join '\')
}
Write-Output '=== RESOLVED DIRECTORY TREE ==='
foreach ($r in $dirs) { Write-Output ((Resolve-Dir $r[0]) + "  <=  " + $r[0]) }

$f2c = @{}
Invoke-MsiViewAll 'SELECT `File`, `Component_` FROM `File`' | ForEach-Object { $f2c[$_[0]] = $_[1] }
$c2d = @{}
Invoke-MsiViewAll 'SELECT `Component`, `Directory_` FROM `Component`' | ForEach-Object { $c2d[$_[0]] = $_[1] }

Write-Output ''
Write-Output '=== FILE -> RESOLVED DIR ==='
$lines = @()
Invoke-MsiViewAll 'SELECT `File`, `FileName` FROM `File`' | ForEach-Object {
    $comp = $f2c[$_[0]]
    $dir = $c2d[$comp]
    $lines += ((Resolve-Dir $dir) + '\' + ($_[1] -split '\|' | Select-Object -Last 1))
}
$lines | Sort-Object | Out-File -FilePath (Join-Path $PSScriptRoot 'filemap.txt') -Encoding utf8
Write-Output ('wrote filemap.txt with ' + $lines.Count + ' rows')
