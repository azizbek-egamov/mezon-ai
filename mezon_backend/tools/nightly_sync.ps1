# MEZON AI — lex.uz bilan tungi sinxronizatsiya (TZ §6.4). Windows Task Scheduler har kuni 02:00 da ishga tushiradi.
#   - Qdrant server ishlamayotgan bo'lsa, vaqtincha yoqiladi va oxirida o'chiriladi;
#   - yakshanba kunlari barcha kodekslar ham qayta tekshiriladi (--check-codes);
#   - jurnal: data\logs\sync_YYYYMMDD.log (natija bazada ham: admin -> "lex.uz sinxronizatsiyalari").
$ErrorActionPreference = "Stop"
$backend = "E:\mezon\mezon_backend"
$qdrant  = "E:\mezon\qdrant_server\qdrant.exe"
$logDir  = Join-Path $backend "data\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("sync_{0:yyyyMMdd}.log" -f (Get-Date))

$started = $null
if (-not (Test-NetConnection -ComputerName 127.0.0.1 -Port 6333 -InformationLevel Quiet -WarningAction SilentlyContinue)) {
    $started = Start-Process -FilePath $qdrant -ArgumentList "--config-path", "E:/mezon/qdrant_server/config.yaml" `
        -WorkingDirectory "E:\mezon\qdrant_server" -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 5
}
try {
    $syncArgs = @("manage.py", "sync_lex")
    if ((Get-Date).DayOfWeek -eq "Sunday") { $syncArgs += "--check-codes" }
    # cmd orqali: Python chiqishi baytma-bayt (UTF-8) faylga yoziladi — PowerShell uni UTF-16 ga aylantirmasin.
    $cmdLine = '"{0}\.venv\Scripts\python.exe" {1} >> "{2}" 2>&1' -f $backend, ($syncArgs -join " "), $log
    Push-Location $backend
    cmd /c $cmdLine
    Pop-Location
} finally {
    if ($started) { Stop-Process -Id $started.Id -ErrorAction SilentlyContinue }
}
