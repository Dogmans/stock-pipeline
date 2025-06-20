# Run-StockPipeline.ps1
<#
.SYNOPSIS
Runs the stock pipeline with the new reporting format.

.DESCRIPTION
This script runs the stock pipeline with various configuration options
and opens the resulting report in your default Markdown viewer.

.PARAMETER Universe
The stock universe to screen (sp500, nasdaq100, russell2000, or custom).

.PARAMETER Strategies
Comma-separated list of screening strategies to run.

.PARAMETER OutputDir
Directory where reports will be saved.

.PARAMETER OpenReport
Whether to automatically open the report when finished.

.EXAMPLE
.\Run-StockPipeline.ps1 -Universe sp500 -Strategies value,growth
Runs the pipeline on SP500 stocks using value and growth strategies.

.EXAMPLE
.\Run-StockPipeline.ps1 -Full
Runs the full pipeline with all strategies and stock universes.
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$Universe = "sp500",
    
    [Parameter(Mandatory=$false)]
    [string]$Strategies = "value,growth",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "output",
      [Parameter(Mandatory=$false)]
    [switch]$OpenReport,
    
    [Parameter(Mandatory=$false)]
    [switch]$Full = $false
)

# Construct the command
$command = "python main.py"

if ($Full) {
    $command += " --full"
}
else {
    $command += " --universe $Universe --strategies $Strategies"
}

$command += " --output $OutputDir"

# Run the pipeline
Write-Host "Running stock pipeline with command: $command" -ForegroundColor Cyan
Invoke-Expression $command

# Check if the report was generated
$reportPath = Join-Path $OutputDir "screening_report.md"
if (Test-Path $reportPath) {
    Write-Host "Report generated successfully at: $reportPath" -ForegroundColor Green
    
    # Open the report if requested
    if ($OpenReport) {
        Write-Host "Opening report..." -ForegroundColor Cyan
        Invoke-Item $reportPath
    }
}
else {
    Write-Host "Report was not generated. Check for errors." -ForegroundColor Red
}

# Display summary
$summaryPath = Join-Path $OutputDir "summary.txt"
if (Test-Path $summaryPath) {
    Write-Host "`nSUMMARY:" -ForegroundColor Yellow
    Get-Content $summaryPath | Write-Host
}
