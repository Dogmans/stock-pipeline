##############################################
# run_tests.ps1
# Stock Pipeline Test Runner
##############################################

param(
    [Parameter(Position = 0)]
    [string]$TestModule = "",

    [Parameter()]
    [switch]$Coverage = $false,

    [Parameter()]
    [switch]$Html = $false,

    [Parameter()]
    [switch]$Verbose = $false,

    [Parameter()]
    [switch]$Help = $false
)

# Function to show help text
function Show-Help {
    Write-Host "Stock Pipeline Test Runner" -ForegroundColor Cyan
    Write-Host "=========================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\run_tests.ps1 [TestModule] [-Coverage] [-Html] [-Verbose] [-Help]"
    Write-Host ""
    Write-Host "Parameters:" -ForegroundColor Yellow
    Write-Host "  TestModule    Specific test module to run (e.g., 'test_cache_manager')"
    Write-Host "  -Coverage     Generate code coverage report"
    Write-Host "  -Html         Generate HTML coverage report (implies -Coverage)"
    Write-Host "  -Verbose      Show verbose output"
    Write-Host "  -Help         Show this help message"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\run_tests.ps1                   # Run all tests"
    Write-Host "  .\run_tests.ps1 test_cache_manager # Run specific test module"
    Write-Host "  .\run_tests.ps1 -Coverage         # Run all tests with coverage report"
    Write-Host "  .\run_tests.ps1 -Html             # Run all tests with HTML coverage report"
    Write-Host ""
}

# Display help if requested
if ($Help) {
    Show-Help
    exit 0
}

# Set the title of the PowerShell window
$host.UI.RawUI.WindowTitle = "Stock Pipeline Test Runner"

# Script banner
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "      Stock Pipeline Test Runner     " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Ensure we are in the right directory (script directory)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Generate the command
if ($Coverage -or $Html) {
    # Check if coverage is installed
    try {
        $coverageVersion = python -c "import coverage; print(coverage.__version__)"
        if ($Verbose) {
            Write-Host "Coverage.py version $coverageVersion detected" -ForegroundColor Green
        }
    } catch {
        Write-Host "Coverage.py is not installed. Installing..." -ForegroundColor Yellow
        python -m pip install coverage
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to install coverage.py. Please install it manually:" -ForegroundColor Red
            Write-Host "pip install coverage" -ForegroundColor Red
            exit 1
        }
    }
    
    # Build test command with coverage
    if ($TestModule) {
        $testArg = "tests.$TestModule"
    } else {
        $testArg = "discover -s tests"
    }
    
    Write-Host "Running tests with coverage..." -ForegroundColor Cyan
    python -m coverage run --source=. -m unittest $testArg
    
    if ($LASTEXITCODE -eq 0) {
        # Generate coverage reports
        Write-Host "`nGenerating coverage report..." -ForegroundColor Cyan
        python -m coverage report
        
        if ($Html) {
            Write-Host "`nGenerating HTML coverage report..." -ForegroundColor Cyan
            python -m coverage html
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "`nHTML coverage report generated in htmlcov directory" -ForegroundColor Green
                Write-Host "Open htmlcov\index.html to view the report"
                
                # Optionally open the report in the default browser
                $openReport = Read-Host "Open HTML report now? (y/n)"
                if ($openReport -eq "y") {
                    Start-Process "htmlcov\index.html"
                }
            }
        }
    }
} else {
    # Run tests without coverage
    if ($TestModule) {
        $testArg = "tests.$TestModule"
        Write-Host "Running tests for module: $TestModule..." -ForegroundColor Cyan
    } else {
        $testArg = "discover -s tests"
        Write-Host "Running all tests..." -ForegroundColor Cyan
    }
    
    if ($Verbose) {
        python -m unittest -v $testArg
    } else {
        python -m unittest $testArg
    }
}

# Display results
if ($LASTEXITCODE -eq 0) {
    Write-Host "`nTests completed successfully!" -ForegroundColor Green
} else {
    Write-Host "`nTests failed with exit code $LASTEXITCODE" -ForegroundColor Red
}

# Add a pause when running from a window so the user can see the results
if ($Host.Name -eq "ConsoleHost") {
    Write-Host "`nPress any key to continue..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
