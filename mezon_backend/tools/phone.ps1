# MEZON AI - telefondagi ilova uchun PC tomoni (USB, LLM siz server - Claude API ga pul ketmaydi).
#   powershell -ExecutionPolicy Bypass -File tools\phone.ps1 start    # Qdrant + server :8011 + USB kuzatuvchi (fonda)
#   powershell -ExecutionPolicy Bypass -File tools\phone.ps1 status
#   powershell -ExecutionPolicy Bypass -File tools\phone.ps1 stop
# Ilova http://localhost:8011 ga murojaat qiladi; USB kuzatuvchi telefon har ulanganda `adb reverse tcp:8011` ni
# qayta o'rnatadi (kabel chiqarilsa yoki telefon qayta yoqilsa - o'zi tiklanadi). Telefonda USB debugging yoqilgan bo'lsin.
# Server: tools\serve.py --nollm --http (waitress, faqat 127.0.0.1). Jurnallar: data\logs\phone_*.log
param([ValidateSet("start", "stop", "status", "watch")][string]$Action = "status")

$backend = "E:\mezon\mezon_backend"
$python = "$backend\.venv\Scripts\python.exe"
$adb = "C:\platform-tools\adb.exe"
$port = 8011
$logDir = Join-Path $backend "data\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Test-Port($p) {
    Test-NetConnection -ComputerName 127.0.0.1 -Port $p -InformationLevel Quiet -WarningAction SilentlyContinue
}

function Get-ServerProcess {
    Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
        Where-Object { $_.CommandLine -match "tools[\\/]serve\.py" -and $_.CommandLine -match "--port\s+$port\b" }
}

function Get-WatcherProcess {
    Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" |
        Where-Object { $_.CommandLine -match "phone\.ps1" -and $_.CommandLine -match "\bwatch\b" }
}

function Get-PhoneState {
    $line = & $adb devices 2>$null | Select-String -Pattern "\tdevice$" | Select-Object -First 1
    if (-not $line) { return "ulanmagan" }
    $reverse = & $adb reverse --list 2>$null | Select-String -Pattern "tcp:$port" -Quiet
    if ($reverse) { "ulangan, adb reverse tcp:$port bor" } else { "ulangan, adb reverse YO'Q" }
}

switch ($Action) {
    "watch" {
        # Telefon ulanishi bilan reverse; uzilguncha kutadi; yana ulanishini kutadi (cheksiz)
        while ($true) {
            & $adb wait-for-device 2>$null
            & $adb reverse "tcp:$port" "tcp:$port" 2>$null | Out-Null
            Add-Content -Path (Join-Path $logDir "phone_watch.log") -Value ("{0:yyyy-MM-dd HH:mm:ss} ulandi, reverse tcp:$port" -f (Get-Date))
            & $adb wait-for-disconnect 2>$null
            Start-Sleep -Seconds 2
        }
    }
    "start" {
        if (-not (Test-Port 6333)) {
            Start-Process -FilePath "E:\mezon\qdrant_server\qdrant.exe" `
                -ArgumentList "--config-path", "E:/mezon/qdrant_server/config.yaml" `
                -WorkingDirectory "E:\mezon\qdrant_server" -WindowStyle Hidden `
                -RedirectStandardOutput (Join-Path $logDir "qdrant.out.log") `
                -RedirectStandardError (Join-Path $logDir "qdrant.log") | Out-Null
        }
        if (-not (Get-ServerProcess)) {
            if (Test-Port $port) { throw "Port $port band (dev_nollm.py?). Avval uni to'xtating." }
            Start-Process -FilePath $python -ArgumentList "tools\serve.py", "--port", "$port", "--nollm", "--http" `
                -WorkingDirectory $backend -WindowStyle Hidden `
                -RedirectStandardOutput (Join-Path $logDir "phone_server.out.log") `
                -RedirectStandardError (Join-Path $logDir "phone_server.log") | Out-Null
        }
        if (-not (Get-WatcherProcess)) {
            Start-Process -FilePath "powershell.exe" -WindowStyle Hidden `
                -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "$backend\tools\phone.ps1", "watch" | Out-Null
        }
        foreach ($i in 1..30) {
            Start-Sleep -Seconds 1
            if (Test-Port $port) { break }
        }
        Write-Output ("Server :$port - " + $(if (Test-Port $port) { "ishlayapti" } else { "ishga tushmadi (data\logs\phone_server.log)" }))
        Start-Sleep -Seconds 2
        Write-Output ("Telefon: " + (Get-PhoneState))
    }
    "stop" {
        Get-WatcherProcess | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Get-ServerProcess | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Write-Output "To'xtatildi (Qdrant boshqa serverlar uchun qoldirildi; kerak bo'lmasa: tools\prod.ps1 stop)"
    }
    "status" {
        Write-Output ("Qdrant 6333: " + $(if (Test-Port 6333) { "ishlayapti" } else { "o'chiq" }))
        Write-Output ("Server $port : " + $(if (Get-ServerProcess) { "ishlayapti" } else { "o'chiq" }))
        Write-Output ("USB kuzatuvchi: " + $(if (Get-WatcherProcess) { "ishlayapti" } else { "o'chiq" }))
        Write-Output ("Telefon: " + (Get-PhoneState))
    }
}
