# MEZON AI - tungi zaxira nusxa (apps/ops, `manage.py backup`). Windows Task Scheduler har kuni 03:30 da ishga tushiradi.
#   - baza + ish fayllari har kuni; yakshanba kunlari Qdrant snapshot ham (--qdrant, ~0.7 GB qo'shiladi);
#   - joy: MEZON_BACKUP_DIR (.env), sukut E:\mezon\backups; eng yangi MEZON_BACKUP_KEEP (7) tasi qoladi;
#   - yaratilgan nusxa darhol tekshiriladi (backup verify);
#   - jurnal: data\logs\backup_YYYYMMDD.log.
# Zaxira MEZON_DATA_KEYS bilan shifrlangan - kalitni alohida (parol menejerida) saqlang.
$ErrorActionPreference = "Stop"
$backend = "E:\mezon\mezon_backend"
$python = "$backend\.venv\Scripts\python.exe"
$logDir = Join-Path $backend "data\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("backup_{0:yyyyMMdd}.log" -f (Get-Date))

$backupArgs = @("manage.py", "backup")
$qdrantUp = Test-NetConnection -ComputerName 127.0.0.1 -Port 6333 -InformationLevel Quiet -WarningAction SilentlyContinue
if ((Get-Date).DayOfWeek -eq "Sunday" -and $qdrantUp) { $backupArgs += "--qdrant" }

Push-Location $backend
try {
    # cmd orqali: Python chiqishi baytma-bayt (UTF-8) faylga yoziladi
    cmd /c ('"{0}" {1} >> "{2}" 2>&1' -f $python, ($backupArgs -join " "), $log)
    if ($LASTEXITCODE -ne 0) { throw "backup xato bilan tugadi (jurnal: $log)" }
    $made = Select-String -Path $log -Pattern "Zaxira: (.+\.mzb)" | Select-Object -Last 1
    if ($made) {
        cmd /c ('"{0}" manage.py backup verify "{1}" >> "{2}" 2>&1' -f $python, $made.Matches[0].Groups[1].Value, $log)
        if ($LASTEXITCODE -ne 0) { throw "zaxira tekshiruvdan o'tmadi (jurnal: $log)" }
    }
} finally {
    Pop-Location
}
