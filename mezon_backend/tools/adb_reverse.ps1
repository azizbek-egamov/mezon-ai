# MEZON AI — telefonni USB orqali PC dagi serverlarga ulash (adb reverse). Telefon ichidagi localhost:PORT = PC:PORT.
#   powershell -ExecutionPolicy Bypass -File tools\adb_reverse.ps1
# USB qayta ulanganda yoki telefon qayta yoqilganda takrorlang. Telefonda: Dasturchi sozlamalari -> USB orqali tuzatish (USB debugging).
#   8010 — Django (asosiy, LLM bilan — pullik)   8011 — LLM siz dev server (tools/dev_nollm.py)   8081 — Metro (Expo dev)
$adb = "C:\platform-tools\adb.exe"
if (-not (Test-Path $adb)) { $adb = "E:\android\Sdk\platform-tools\adb.exe" }

$devices = & $adb devices | Select-Object -Skip 1 | Where-Object { $_ -match "\tdevice$" }
if (-not $devices) {
    Write-Output "Qurilma topilmadi. USB kabel va 'USB orqali tuzatish' ni tekshiring; telefonda ruxsat so'rovini tasdiqlang."
    & $adb devices
    exit 1
}
foreach ($port in 8010, 8011, 8081) {
    & $adb reverse "tcp:$port" "tcp:$port" | Out-Null
}
Write-Output "Ulandi: $($devices -join ', ')"
& $adb reverse --list
