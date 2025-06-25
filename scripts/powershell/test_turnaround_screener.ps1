# Test Turnaround Screener
# This script runs the turnaround screener test script and captures the output

$outputDir = "output\turnaround_analysis"

# Create output directory if it doesn't exist
if (-not (Test-Path $outputDir)) {
    New-Item -Path $outputDir -ItemType Directory -Force | Out-Null
    Write-Host "Created output directory: $outputDir"
}

# Set log file path
$logFile = "$outputDir\test_run_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# Run the Python script and capture output
Write-Host "Running turnaround screener test script..."
Write-Host "Output will be saved to $logFile"
Write-Host ""

try {
    # Execute the Python script
    python scripts\python\test_turnaround_screener.py | Tee-Object -FilePath $logFile
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "Test completed successfully."
        Write-Host "Log saved to $logFile"
        
        # Check if any CSV results were generated
        $csvFiles = Get-ChildItem -Path $outputDir -Filter "*.csv"
        if ($csvFiles.Count -gt 0) {
            Write-Host ""
            Write-Host "Results files generated:"
            foreach ($file in $csvFiles) {
                $recordCount = (Import-Csv $file.FullName | Measure-Object).Count
                Write-Host "  - $($file.Name): $recordCount records"
            }
        }
    } else {
        Write-Host "Error: Python script failed with exit code $LASTEXITCODE"
    }
} catch {
    Write-Host "Error executing script: $_"
}
