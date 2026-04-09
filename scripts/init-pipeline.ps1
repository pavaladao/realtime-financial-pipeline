<#
.SYNOPSIS
  Brings up infra and runs PySpark streaming in this terminal until you stop it.

.DESCRIPTION
  1. docker compose up -d
  2. Waits for Kafka (9092), Schema Registry HTTP, Postgres (5433)
  3. Runs src/producers/update_schema.py
  4. Creates Kafka topic trades-data if missing
  5. Starts Spark streaming in the foreground; the job waits for the producer — start the producer in another terminal when ready (see message below). Ctrl+C stops Spark.

.PARAMETER Build
  Pass --build to docker compose up.

.PARAMETER SkipCompose
  Skip docker compose when the stack is already running.

.EXAMPLE
  .\scripts\init-pipeline.ps1
  .\scripts\init-pipeline.ps1 -SkipCompose
#>
[CmdletBinding()]
param(
    [switch]$Build,
    [switch]$SkipCompose
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$SparkPackages = "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3,org.postgresql:postgresql:42.7.3"

function Wait-TcpPort {
    param(
        [string]$HostName = "127.0.0.1",
        [int]$Port,
        [int]$TimeoutSec = 180
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    Write-Host "Waiting for $HostName`:$Port (up to ${TimeoutSec}s)..."
    while ((Get-Date) -lt $deadline) {
        try {
            $client = New-Object System.Net.Sockets.TcpClient
            $client.Connect($HostName, $Port)
            $client.Close()
            Write-Host "  $HostName`:$Port is open."
            return
        }
        catch {
            Start-Sleep -Seconds 2
        }
    }
    throw "Timeout waiting for TCP $HostName`:$Port"
}

function Wait-SchemaRegistryHttp {
    param([int]$TimeoutSec = 180)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $url = "http://127.0.0.1:8081/subjects"
    Write-Host "Waiting for Schema Registry HTTP at $url (up to ${TimeoutSec}s)..."
    while ((Get-Date) -lt $deadline) {
        try {
            $null = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5 -Method Get
            Write-Host "  Schema Registry is responding."
            return
        }
        catch {
            Start-Sleep -Seconds 2
        }
    }
    throw "Timeout waiting for Schema Registry HTTP readiness"
}

function Resolve-Python {
    $candidates = @(
        (Join-Path $RepoRoot ".venv\Scripts\python.exe"),
        (Join-Path $RepoRoot "venv\Scripts\python.exe")
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { return $p }
    }
    return "python"
}

# --- 1. docker compose up -d ---
if (-not $SkipCompose) {
    $composeArgs = @("compose", "up", "-d")
    if ($Build) { $composeArgs += "--build" }
    Write-Host "Running: docker $($composeArgs -join ' ')"
    & docker @composeArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

# --- 2. Wait for Kafka (9092), Schema Registry HTTP, Postgres (5433) ---
Wait-TcpPort -Port 9092
Wait-TcpPort -Port 8081
Wait-SchemaRegistryHttp
Wait-TcpPort -Port 5433

# --- 3. src/producers/update_schema.py ---
$python = Resolve-Python
$env:PYTHONPATH = $RepoRoot
Write-Host "Registering schema with: $python"
& $python -m src.producers.update_schema
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# --- 4. Kafka topic trades-data (if missing) ---
Write-Host "Ensuring Kafka topic 'trades-data' exists..."
& docker exec kafka kafka-topics --bootstrap-server kafka:29092 --create --if-not-exists --topic trades-data --partitions 1 --replication-factor 1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# --- 5. Spark streaming (waits for producer / Kafka data) ---
Write-Host ""
Write-Host "-------------------------------------------------------------------"
Write-Host "Spark will start below and block until you press Ctrl+C."
Write-Host "Start the producer in another terminal when you are ready, e.g.:"
Write-Host "  cd `"$RepoRoot`""
Write-Host "  `$env:PYTHONPATH = `"$RepoRoot`""
Write-Host "  & `"$python`" -m src.producers.producer"
Write-Host "-------------------------------------------------------------------"
Write-Host ""
Write-Host "Starting Spark Structured Streaming..."
Write-Host ""

$submitArgs = @(
    "exec", "-e", "PYTHONUNBUFFERED=1", "-it", "spark-driver",
    "spark-submit",
    "--packages", $SparkPackages,
    "--master", "spark://spark-master:7077",
    "--deploy-mode", "client",
    "src/processors/streaming_processor.py"
)
& docker @submitArgs
exit $LASTEXITCODE
