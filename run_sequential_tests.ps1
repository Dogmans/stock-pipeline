##############################################
# run_sequential_tests.ps1
# Stock Pipeline Sequential Test Runner
##############################################

param(
    [Parameter()]
    [switch]$ContinueOnFailure = $false,
    
    [Parameter()]
    [switch]$DetailedOutput = $false,
    
    [Parameter()]
    [string]$StartStage = "",
    
    [Parameter()]
    [switch]$SkipSlowTests = $false,
    
    [Parameter()]
    [switch]$Help = $false
)

# Function to show help text
function Show-TestHelp {
    Write-Host "Stock Pipeline Sequential Test Runner" -ForegroundColor Cyan
    Write-Host "=====================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\run_sequential_tests.ps1 [-ContinueOnFailure] [-Verbose] [-StartStage <stageName>] [-SkipSlowTests] [-Help]"
    Write-Host ""
    Write-Host "Parameters:" -ForegroundColor Yellow
    Write-Host "  -ContinueOnFailure    Continue running tests for next stages even if a stage fails"
    Write-Host "  -Verbose              Show detailed test output"
    Write-Host "  -StartStage <name>    Start testing from a specific stage (e.g., 'Data Processing')"
    Write-Host "  -SkipSlowTests        Skip tests that typically take longer to run"
    Write-Host "  -Help                 Show this help message"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\run_sequential_tests.ps1                          # Run all tests, stop on first failure"
    Write-Host "  .\run_sequential_tests.ps1 -ContinueOnFailure       # Run all tests regardless of failures"
    Write-Host "  .\run_sequential_tests.ps1 -StartStage 'Screening'  # Start from Screening stage"
    exit
}

# Display help if requested
if ($Help) {
    Show-TestHelp
}

# Set the title of the PowerShell window
$host.UI.RawUI.WindowTitle = "Stock Pipeline Sequential Test Runner"

# Script banner
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Stock Pipeline Sequential Testing  " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Ensure we are in the right directory (script directory)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Define test stages and their modules
$stages = @(
    @{
        Name = "Configuration & Utilities"
        Tests = @("test_config", "test_utils")
        Description = "Testing configuration settings and utility functions"
    },
    @{
        Name = "Cache Manager"
        Tests = @("test_cache_manager")
        Description = "Testing caching functionality"
    },
    @{
        Name = "Stock Universe"
        Tests = @("test_universe")
        Description = "Testing stock universe selection"
    },
    @{
        Name = "Data Fetching"
        Tests = @("test_market_data")
        Description = "Testing data collection from APIs"
    },
    @{
        Name = "Data Processing"
        Tests = @("test_data_processing")
        Description = "Testing data processing and calculations"
    },
    @{
        Name = "Screening"
        Tests = @("test_screeners")
        Description = "Testing screening strategies"
    }
)

# Track overall success/failure
$allPassed = $true
$stagesPassed = 0
$failedStages = @()
$foundStartStage = ($StartStage -eq "")

# Loop through each stage
foreach ($stage in $stages) {
    Write-Host "------------------------------------" -ForegroundColor DarkCyan
    Write-Host "STAGE: $($stage.Name)" -ForegroundColor Cyan
    Write-Host $stage.Description
    Write-Host "------------------------------------" -ForegroundColor DarkCyan
    
    $stagePassed = $true
      # Check if we should skip to a later stage
    if ($StartStage -and $stage.Name -ne $StartStage -and $foundStartStage -ne $true) {
        Write-Host "Skipping stage '$($stage.Name)' (waiting for '$StartStage')" -ForegroundColor DarkGray
        continue
    }
    
    # Mark that we've found the start stage
    if ($StartStage -and $stage.Name -eq $StartStage) {
        $foundStartStage = $true
    }
    
    # Run each test module in this stage
    foreach ($test in $stage.Tests) {
        # Skip slow tests if requested
        if ($SkipSlowTests -and $test -in @("test_market_data")) {
            Write-Host "Skipping slow test: $test..." -ForegroundColor DarkYellow
            continue
        }
        
        Write-Host "Running test module: $test..." -ForegroundColor Yellow
        
        # Run the test with appropriate verbosity
        if ($Verbose) {
            python -m unittest -v tests.$test
        } else {
            python -m unittest tests.$test
        }
        
        # Check if the test passed
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ $test passed" -ForegroundColor Green
        } else {
            Write-Host "❌ $test failed" -ForegroundColor Red
            $stagePassed = $false
            $allPassed = $false
        }
    }    # Report stage result
    if ($stagePassed) {
        Write-Host "Stage '$($stage.Name)' PASSED" -ForegroundColor Green
        $stagesPassed++
    } else {
        Write-Host "Stage '$($stage.Name)' FAILED" -ForegroundColor Red
        $failedStages += $stage.Name
        
        # Check if we should continue despite failures
        if (-not $ContinueOnFailure) {
            Write-Host "Stopping sequential tests due to failures." -ForegroundColor Yellow
            Write-Host "To run all tests despite failures, use: .\run_sequential_tests.ps1 -ContinueOnFailure" -ForegroundColor DarkYellow
            break
        } else {
            Write-Host "Continuing to next stage despite failures (-ContinueOnFailure flag is set)." -ForegroundColor DarkYellow
        }
    }
    
    # Add spacing between stages
    Write-Host ""
}

# Report overall results
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Sequential Testing Results" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Stages Passed: $stagesPassed / $($stages.Count)" -ForegroundColor Cyan

if ($allPassed) {
    Write-Host "ALL STAGES PASSED! 🎉" -ForegroundColor Green
} else {
    Write-Host "SOME STAGES FAILED! ⚠️" -ForegroundColor Red
    Write-Host "Failed stages:" -ForegroundColor Red
    foreach ($failedStage in $failedStages) {
        Write-Host "  - $failedStage" -ForegroundColor Red
    }
}

# Add a pause when running from a window so the user can see the results
if ($Host.Name -eq "ConsoleHost") {
    Write-Host "`nPress any key to continue..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
