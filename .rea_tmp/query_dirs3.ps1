param([string]$MsiPath)
$ErrorActionPreference = 'Stop'
$installer = New-Object -ComObject WindowsInstaller.Installer
$global:MSI_ROWS = $null

function Invoke-MsiViewAll([string]$Sql) {
    $db = $installer.GetType().InvokeMember('OpenDatabase','InvokeMethod',$null,$installer,@($MsiPath, 0))
    $view = $db.GetType().InvokeMember('OpenView','InvokeMethod',$null,$db,@($Sql))
    $view.GetType().InvokeMember('Execute','InvokeMethod',$null,$view,$null)
    $rows = New-Object System.Collections.Generic.List[object]
    while ($true) {
        $rec = $view.GetType().InvokeMember('Fetch','InvokeMethod',$null,$view,$null)
        if ($null -eq $rec) { break }
        $colCount = [int]$rec.GetType().InvokeMember('FieldCount','GetProperty',$null,$rec,$null)
        $vals = New-Object 'System.Collections.Generic.List[string]'
        for ($i = 1; $i -le $colCount; $i++) {
            $vals.Add([string]$rec.GetType().InvokeMember('StringData','GetProperty',$null,$rec,$i))
        }
        $rows.Add($vals.ToArray())
    }
    $view.GetType().InvokeMember('Close','InvokeMethod',$null,$view,$null) | Out-Null
    [Runtime.InteropServices.Marshal]::ReleaseComObject($view) | Out-Null
    [Runtime.InteropServices.Marshal]::ReleaseComObject($db) | Out-Null
    $global:MSI_ROWS = $rows.ToArray()
    return
}

# 1. Directory table
Invoke-MsiViewAll 'SELECT * FROM `Directory`'
$dirs = $global:MSI_ROWS
$dirMap = @{}
$dirParent = @{}
foreach ($r in $dirs) { $dirMap[$r[0]] = $r[2]; $dirParent[$r[0]] = $r[1] }
function Resolve-Dir([string]$d) {
    $parts = New-Object System.Collections.Generic.List[string]
    $cur = $d
    $guard = 0
    while ($cur -and $dirMap.ContainsKey($cur) -and $guard -lt 50) {
        $name = ($dirMap[$cur] -split '\|')[-1]
        $parts.Insert(0, $name)
        $cur = $dirParent[$cur]
        $guard++
    }
    return ($parts -join '\')
}

Write-Output '=== RESOLVED DIRECTORY TREE ==='
foreach ($r in $dirs) { Write-Output ((Resolve-Dir $r[0]) + "  <=  " + $r[0]) }

# 2. file -> component -> dir
$f2c = @{}
Invoke-MsiViewAll 'SELECT `File`, `Component_` FROM `File`'
foreach ($r in $global:MSI_ROWS) { $f2c[$r[0]] = $r[1] }
$c2d = @{}
Invoke-MsiViewAll 'SELECT `Component`, `Directory_` FROM `Component`'
foreach ($r in $global:MSI_ROWS) { $c2d[$r[0]] = $r[1] }

$lines = New-Object System.Collections.Generic.List[string]
Invoke-MsiViewAll 'SELECT `File`, `FileName` FROM `File`'
foreach ($r in $global:MSI_ROWS) {
    $dir = $c2d[$f2c[$r[0]]]
    $lines.Add((Resolve-Dir $dir) + '\' + (($r[1] -split '\|')[-1]))
}
$lines | Sort-Object | Out-File -FilePath (Join-Path $PSScriptRoot 'filemap.txt') -Encoding utf8
Write-Output ('wrote filemap.txt with ' + $lines.Count + ' rows')
