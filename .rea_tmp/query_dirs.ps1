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
        $colCount = [int]$rec.GetType().InvokeMember('FieldCount','GetProperty',$null,$rec,$null)
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

Write-Output '=== DIRECTORY TABLE ==='
Invoke-MsiView 'SELECT `Directory`, `DirectoryParent`, `DefaultDir` FROM `Directory`' | ForEach-Object { Write-Output $_ }

Write-Output ''
Write-Output '=== COMPONENT -> DIRECTORY (cores-related, via files whose target path contains cores) ==='
# file -> component
$f2c = @{}
Invoke-MsiView 'SELECT `File`, `Component_` FROM `File`' | ForEach-Object {
    $parts = $_ -split "`t"; $f2c[$parts[0]] = $parts[1]
}
$c2d = @{}
Invoke-MsiView 'SELECT `Component`, `Directory_` FROM `Component`' | ForEach-Object {
    $parts = $_ -split "`t"; $c2d[$parts[0]] = $parts[1]
}
# print file table with resolved directory key for all files (fileid | dirkey)
Invoke-MsiView 'SELECT `File`, `FileName` FROM `File`' | ForEach-Object {
    $parts = $_ -split "`t"
    $comp = $f2c[$parts[0]]
    $dir = $c2d[$comp]
    Write-Output ("$dir`t" + $parts[1])
} | Sort-Object | Out-File -FilePath (Join-Path $PSScriptRoot 'filemap.txt') -Encoding utf8
Write-Output 'wrote filemap.txt'
