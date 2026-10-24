
$installer = New-Object -ComObject WindowsInstaller.Installer
$db = $installer.GetType().InvokeMember('OpenDatabase','InvokeMethod',$null,$installer,@('F:\AI\霸王三国志\XiaoJi_v1.1.3.msi',0))
$queries = @(
  'SELECT * FROM `Directory`',
  'SELECT `DefaultDir` FROM `Directory`',
  'SELECT * FROM `Component` WHERE `KeyPath` IS NOT NULL'
)
foreach ($sql in $queries) {
  try {
    $view = $db.GetType().InvokeMember('OpenView','InvokeMethod',$null,$db,@($sql))
    $view.GetType().InvokeMember('Execute','InvokeMethod',$null,$view,$null)
    $n = 0
    while ($true) { $rec = $view.GetType().InvokeMember('Fetch','InvokeMethod',$null,$view,$null); if ($null -eq $rec) { break }
      $n++
      if ($n -le 5) {
        $v1 = $rec.GetType().InvokeMember('StringData','GetProperty',$null,$rec,1)
        $v2 = $rec.GetType().InvokeMember('StringData','GetProperty',$null,$rec,2)
        $v3 = $rec.GetType().InvokeMember('StringData','GetProperty',$null,$rec,3)
        Write-Output ("OK: " + $v1 + "|" + $v2 + "|" + $v3)
      } }
    Write-Output ("TOTAL: " + $n)
  } catch { Write-Output ('FAILED: ' + $_.Exception.Message) }
}
