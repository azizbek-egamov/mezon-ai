# MEZON AI — dev serverlarni terminaldan boshqarish (Qdrant + Django).
#   powershell -ExecutionPolicy Bypass -File tools\dev.ps1 start    # Qdrant (6333) va Django (8010) fonda
#   powershell -ExecutionPolicy Bypass -File tools\dev.ps1 status
#   powershell -ExecutionPolicy Bypass -File tools\dev.ps1 stop     # ikkalasini to'xtatadi (RAM bo'shaydi)
# Jurnallar: data\logs\qdrant*.log, data\logs\django*.log. Brauzer: http://127.0.0.1:8010/
param([ValidateSet("start", "stop", "status")][string]$Action = "status")

$backend = "E:\mezon\mezon_backend"
$logDir = Join-Path $backend "data\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Test-Port($port) {
    Test-NetConnection -ComputerName 127.0.0.1 -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue
}

function Get-DjangoProcess {
    Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
        Where-Object { $_.CommandLine -match "manage.py runserver 127.0.0.1:8010" }
}

switch ($Action) {
    "start" {
        if (-not (Test-Port 6333)) {
            Start-Process -FilePath "E:\mezon\qdrant_server\qdrant.exe" `
                -ArgumentList "--config-path", "E:/mezon/qdrant_server/config.yaml" `
                -WorkingDirectory "E:\mezon\qdrant_server" -WindowStyle Hidden `
                -RedirectStandardOutput (Join-Path $logDir "qdrant.out.log") `
                -RedirectStandardError (Join-Path $logDir "qdrant.log") | Out-Null
            Start-Sleep -Seconds 3
        }
        if (-not (Test-Port 8010)) {
            Start-Process -FilePath "$backend\.venv\Scripts\python.exe" `
                -ArgumentList "manage.py", "runserver", "127.0.0.1:8010", "--noreload" `
                -WorkingDirectory $backend -WindowStyle Hidden `
                -RedirectStandardOutput (Join-Path $logDir "django.out.log") `
                -RedirectStandardError (Join-Path $logDir "django.log") | Out-Null
        }
        Write-Output "Qdrant: http://127.0.0.1:6333  |  MEZON: http://127.0.0.1:8010/ (modellar ~30 s yuklanadi)"
    }
    "stop" {
        Get-DjangoProcess | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Get-Process qdrant -ErrorAction SilentlyContinue | Stop-Process -Force
        Write-Output "To'xtatildi"
    }
    "status" {
        Write-Output ("Qdrant 6333: " + $(if (Test-Port 6333) { "ishlayapti" } else { "o'chiq" }))
        Write-Output ("Django 8010: " + $(if (Test-Port 8010) { "ishlayapti" } else { "o'chiq" }))
    }
}
