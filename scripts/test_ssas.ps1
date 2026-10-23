<#
.SYNOPSIS
    Diagnostics utility to query the active Power BI Desktop Analysis Services instance via ADOMD.NET.
.PARAMETER Port
    Optional localhost port of the active msmdsrv.exe instance. If omitted, attempts to auto-detect.
#>
param(
    [int]$Port = 0
)

# 1. Locate AdomdClient assembly
$adomdCandidates = @(
    "C:\Program Files\Microsoft Power BI Desktop\bin\Microsoft.PowerBI.AdomdClient.dll",
    "C:\Program Files\Microsoft Power BI Desktop Store App\bin\Microsoft.PowerBI.AdomdClient.dll"
)
$adomdPath = $adomdCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $adomdPath) {
    Write-Warning "Microsoft.PowerBI.AdomdClient.dll not found in standard Power BI Desktop installation directories."
    exit 1
}

Add-Type -Path $adomdPath

# 2. Auto-detect port if not provided
if ($Port -eq 0) {
    $pbi = Get-Process -Name "PBIDesktop" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pbi) {
        $msmdsrv = Get-CimInstance Win32_Process -Filter "Name = 'msmdsrv.exe'" | Where-Object { $_.ParentProcessId -eq $pbi.Id } | Select-Object -First 1
        if ($msmdsrv) {
            $listening = netstat -ano | Select-String "LISTENING" | Select-String "$($msmdsrv.ProcessId)"
            if ($listening -match ":(\d+)\s+.*LISTENING") {
                $Port = [int]$matches[1]
                Write-Host "Auto-detected Analysis Services instance for PID $($pbi.Id) on port $Port"
            }
        }
    }
}

if ($Port -eq 0) {
    Write-Warning "Power BI Desktop instance not detected. Please open InsightFlow.pbip in Power BI Desktop or specify port: .\test_ssas.ps1 -Port <port>"
    exit 1
}

$connStr = "Data Source=localhost:$Port;"
$conn = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection($connStr)
try {
    $conn.Open()
    Write-Host "SUCCESS: Connected to Analysis Services on localhost:$Port via Microsoft.PowerBI.AdomdClient!"

    $tables = @("Sales", "Inventory", "Product", "Customer", "Location", "Date", "DataQualityReconciliation")
    foreach ($t in $tables) {
        try {
            $cmd = $conn.CreateCommand()
            $cmd.CommandText = "EVALUATE ROW(`"Count`", COUNTROWS('$t'))"
            $reader = $cmd.ExecuteReader()
            if ($reader.Read()) {
                Write-Host "Table '$t': $($reader[0]) rows"
            }
            $reader.Close()
        } catch {
            Write-Host "Table '$t': ERROR -> $($_.Exception.Message)"
        }
    }

    Write-Host "`n--- Testing DataQualityReconciliation Measures ---"
    $measures = @(
        "SUM(DataQualityReconciliation[raw_ingested])",
        "SUM(DataQualityReconciliation[clean_loaded])",
        "[Total Raw Records]",
        "[Total Clean Records]",
        "[Overall Preservation Rate %]"
    )
    foreach ($m in $measures) {
        try {
            $cmd = $conn.CreateCommand()
            $cmd.CommandText = "EVALUATE ROW(`"Val`", $m)"
            $reader = $cmd.ExecuteReader()
            if ($reader.Read()) {
                Write-Host "DAX: $m -> $($reader[0])"
            }
            $reader.Close()
        } catch {
            Write-Host "DAX: $m -> ERROR: $($_.Exception.Message)"
        }
    }

    Write-Host "`n--- Testing Location[region] + Sales[Revenue] ---"
    try {
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = "EVALUATE SUMMARIZECOLUMNS('Location'[region], `"Revenue`", [Revenue])"
        $reader = $cmd.ExecuteReader()
        Write-Host "SUCCESS: Location[region] + Sales[Revenue]:"
        while ($reader.Read()) {
            Write-Host "  Region: $($reader[0]), Revenue: $($reader[1])"
        }
        $reader.Close()
    } catch {
        Write-Host "Location[region] + Sales[Revenue] -> ERROR: $($_.Exception.Message)"
    }

    Write-Host "`n--- Testing Location[region] simple column ---"
    try {
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = "EVALUATE VALUES('Location'[region])"
        $reader = $cmd.ExecuteReader()
        Write-Host "SUCCESS: Location[region] values:"
        while ($reader.Read()) {
            Write-Host "  Region: $($reader[0])"
        }
        $reader.Close()
    } catch {
        Write-Host "Location[region] -> ERROR: $($_.Exception.Message)"
    }

} finally {
    $conn.Close()
}
