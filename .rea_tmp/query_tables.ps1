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

Write-Output '=== FILE TABLE (file, component, size, version, language, directory) ==='
$rows = Invoke-MsiView 'SELECT `File`, `Component_`, `FileSize`, `Version`, `Language` FROM `File`'
Write-Output ("Total files: " + $rows.Count)
foreach ($r in $rows) { Write-Output $r }

Write-Output ''
Write-Output '=== COMPONENT -> DIRECTORY ==='
Invoke-MsiView 'SELECT `Component`, `Directory_` FROM `Component`'

Write-Output ''
Write-Output '=== CUSTOMACTION ==='
try { Invoke-MsiView 'SELECT `CustomAction`, `Type`, `Source`, `Target` FROM `CustomAction`' } catch { Write-Output "(no customaction table)" }

Write-Output ''
Write-Output '=== SHORTCUT ==='
try { Invoke-MsiView 'SELECT `Name`, `Directory_`, `Target` FROM `Shortcut`' } catch { Write-Output "(no shortcut table)" }

Write-Output ''
Write-Output '=== REGISTRY (root, key, name, value) ==='
try { Invoke-MsiView 'SELECT `Root`, `Key`, `Name`, `Value` FROM `Registry`' } catch { Write-Output "(no registry table)" }

Write-Output ''
Write-Output '=== MEDIA (cab) ==='
try { Invoke-MsiView 'SELECT `DiskId`, `Cabinet` FROM `Media`' } catch { Write-Output "(no media table)" }

Write-Output ''
Write-Output '=== DIRECTORY ==='
try { Invoke-MsiView 'SELECT `Directory`, `DirectoryParent`, `DefaultDir` FROM `Directory`' } catch { Write-Output "(no directory table)" }
