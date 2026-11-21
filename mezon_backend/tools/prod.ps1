# MEZON AI - production serverni boshqarish (waitress + Qdrant + Cloudflare Tunnel).
#   powershell -ExecutionPolicy Bypass -File tools\prod.ps1 build    # veb/admin SPA build + collectstatic
#   powershell -ExecutionPolicy Bypass -File tools\prod.ps1 start    # Qdrant, server (:8010), tunnel (config.yml bo'lsa)
#   powershell -ExecutionPolicy Bypass -File tools\prod.ps1 status
#   powershell -ExecutionPolicy Bypass -File tools\prod.ps1 stop
# Server faqat 127.0.0.1 da tinglaydi; tashqaridan - faqat tunnel orqali (HTTPS Cloudflare da).
# Tunnel sozlamasi: tools\cloudflared\config.yml (namuna: config.example.yml; README "Production tarmoq").
# Jurnallar: data\logs\prod_server*.log, data\logs\cloudflared.log, data\logs\mezon.log (Django).
# dev.ps1 (runserver :8010) bilan bir vaqtda ishlamaydi - avval uni to'xtating.
param([ValidateSet("build", "start", "stop", "status")][string]$Action = "status")

$backend = "E:\mezon\mezon_backend"
$frontend = "E:\mezon\frontend"
$python = "$backend\.venv\Scripts\python.exe"
$cloudflared = "E:\cloudflared\cloudflared.exe"
$tunnelConfig = "$backend\tools\cloudflared\config.yml"
$port = 8010
$logDir = Join-Path $backend "data\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Test-Port($p) {
    Test-NetConnection -ComputerName 127.0.0.1 -Port $p -InformationLevel Quiet -WarningAction SilentlyContinue
}

function Get-ServerProcess {
    Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
        Where-Object { $_.CommandLine -match "tools[\\/]serve\.py" -and $_.CommandLine -match "--port\s+$port\b" }
}

function Get-TunnelProcess {
    Get-CimInstance Win32_Process -Filter "Name = 'cloudflared.exe'" |
        Where-Object { $_.CommandLine -match "config\.yml" }
}

function Get-Health {
    try { (Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 "http://127.0.0.1:$port/api/v1/health").Content }
    catch { if ($_.Exception.Response) { "degraded (HTTP $([int]$_.Exception.Response.StatusCode))" } else { "javob yo'q" } }
}

function Invoke-Collectstatic {
    $env:DJANGO_DEBUG = "0"
    Push-Location $backend
    & $python manage.py collectstatic --noinput
    $code = $LASTEXITCODE
    Pop-Location
    Remove-Item Env:DJANGO_DEBUG
    if ($code -ne 0) { throw "collectstatic xato bilan tugadi" }
}

switch ($Action) {
    "build" {
        Push-Location $frontend
        npm run build -w @mezon/web
        if ($LASTEXITCODE -ne 0) { Pop-Location; throw "veb build xato" }
        npm run build -w @mezon/admin
        if ($LASTEXITCODE -ne 0) { Pop-Location; throw "admin build xato" }
        Pop-Location
        Invoke-Collectstatic
        Write-Output "Build tayyor. Ishlab turgan server bo'lsa - qayta ishga tushiring (stop, start)."
    }
    "start" {
        if (Get-ServerProcess) { Write-Output "Server allaqachon ishlayapti"; break }
        if (Test-Port $port) { throw "Port $port band (dev.ps1 serveri?). Avval: tools\dev.ps1 stop" }
        if (-not (Test-Port 6333)) {
            Start-Process -FilePath "E:\mezon\qdrant_server\qdrant.exe" `
                -ArgumentList "--config-path", "E:/mezon/qdrant_server/config.yaml" `
                -WorkingDirectory "E:\mezon\qdrant_server" -WindowStyle Hidden `
                -RedirectStandardOutput (Join-Path $logDir "qdrant.out.log") `
                -RedirectStandardError (Join-Path $logDir "qdrant.log") | Out-Null
            Start-Sleep -Seconds 3
        }
        Invoke-Collectstatic
        Start-Process -FilePath $python -ArgumentList "tools\serve.py", "--port", "$port" `
            -WorkingDirectory $backend -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $logDir "prod_server.out.log") `
            -RedirectStandardError (Join-Path $logDir "prod_server.log") | Out-Null
        $ready = $false
        foreach ($i in 1..30) {
            Start-Sleep -Seconds 2
            if (Test-Port $port) { $ready = $true; break }
        }
        if (-not $ready) { throw "Server 60 s ichida ishga tushmadi - data\logs\prod_server.log ni ko'ring" }
        Write-Output "Server: http://127.0.0.1:$port/  holat: $(Get-Health)"
        if (Test-Path $tunnelConfig) {
            Start-Process -FilePath $cloudflared `
                -ArgumentList "tunnel", "--no-autoupdate", "--config", $tunnelConfig, "--logfile", (Join-Path $logDir "cloudflared.log"), "run" `
                -WindowStyle Hidden | Out-Null
            Write-Output "Tunnel ishga tushirildi (jurnal: data\logs\cloudflared.log)"
        } else {
            Write-Output "Tunnel sozlanmagan ($tunnelConfig yo'q) - server faqat lokal"
        }
    }
    "stop" {
        Get-TunnelProcess | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Get-ServerProcess | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Get-Process qdrant -ErrorAction SilentlyContinue | Stop-Process -Force
        Write-Output "To'xtatildi"
    }
    "status" {
        Write-Output ("Qdrant 6333: " + $(if (Test-Port 6333) { "ishlayapti" } else { "o'chiq" }))
        Write-Output ("Server $port : " + $(if (Get-ServerProcess) { "ishlayapti - $(Get-Health)" } else { "o'chiq" }))
        Write-Output ("Tunnel: " + $(if (Get-TunnelProcess) { "ishlayapti" } elseif (Test-Path $tunnelConfig) { "o'chiq" } else { "sozlanmagan" }))
    }
}
