##############################################
# auto_fix_and_test.ps1
# Automatically fixes common issues and runs tests
##############################################

param(
    [Parameter()]
    [switch]$FixOnly = $false,
    
    [Parameter()]
    [switch]$RunOnly = $false,
    
    [Parameter()]
    [switch]$Help = $false
)

# Function to show help text
function Show-AutoFixHelp {
    Write-Host "Stock Pipeline Auto-Fix and Test Runner" -ForegroundColor Cyan
    Write-Host "=====================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\auto_fix_and_test.ps1 [-FixOnly] [-RunOnly] [-Help]"
    Write-Host ""
    Write-Host "Parameters:" -ForegroundColor Yellow
    Write-Host "  -FixOnly       Only fix common issues, don't run tests"
    Write-Host "  -RunOnly       Only run tests, don't attempt fixes"
    Write-Host "  -Help          Show this help message"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\auto_fix_and_test.ps1              # Run fixes and tests"
    Write-Host "  .\auto_fix_and_test.ps1 -FixOnly     # Run only fixes"
    Write-Host "  .\auto_fix_and_test.ps1 -RunOnly     # Run only tests"
    exit
}

# Display help if requested
if ($Help) {
    Show-AutoFixHelp
}

# Script banner
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Stock Pipeline Auto-Fix and Test   " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Ensure we are in the right directory (script directory)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Only do fixes if not RunOnly
if (-not $RunOnly) {
    Write-Host "Applying common fixes..." -ForegroundColor Yellow
    
    # Fix 1: Check and create __init__.py files
    Write-Host "Checking for missing __init__.py files..."
    
    if (-not (Test-Path "tests/__init__.py")) {
        Write-Host "Creating tests/__init__.py" -ForegroundColor Green
        "" | Set-Content "tests/__init__.py"
    }
      # Fix 2: Check for syntax errors in Python files
    Write-Host "Checking for syntax errors in Python files..."
    
    $pythonFiles = Get-ChildItem -Path "*.py", "tests/*.py" -File
    $hasErrors = $false
    
    foreach ($file in $pythonFiles) {
        Write-Host "  Checking $($file.Name)..." -NoNewline
        $result = python -m py_compile $file.FullName 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host " OK" -ForegroundColor Green
        } else {
            Write-Host " ERROR" -ForegroundColor Red
            Write-Host $result -ForegroundColor Red
            $hasErrors = $true
        }
    }
    
    # Fix 3: Check test discovery issues
    Write-Host "Checking test discovery for test_utils.py..."
    python -c "import unittest; loader = unittest.TestLoader(); print(loader.loadTestsFromName('tests.test_utils'))" 2>&1
    
    # Inspect test_utils.py content
    Write-Host "Displaying content of test_utils.py for verification..."
    Get-Content -Path "tests/test_utils.py" | ForEach-Object { 
        if ($_ -match "class TestUtils") {
            Write-Host $_ -ForegroundColor Green 
        } elseif ($_ -match "def test_") {
            Write-Host $_ -ForegroundColor Cyan
        } else {
            Write-Host $_
        }
    }
    
    if ($hasErrors) {
        Write-Host "Syntax errors found. Please fix them manually before running tests." -ForegroundColor Red
        exit 1
    }
    
    # Fix 3: Check for necessary directories
    Write-Host "Ensuring necessary directories exist..."
    
    $directories = @("data", "data/cache", "results")
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            Write-Host "  Creating directory: $dir" -ForegroundColor Green
            New-Item -ItemType Directory -Path $dir | Out-Null
        }
    }
    
    Write-Host "All common fixes applied successfully." -ForegroundColor Green
    Write-Host ""
}

# Only run tests if not FixOnly
if (-not $FixOnly) {
    Write-Host "Running sequential tests..." -ForegroundColor Yellow
    Write-Host ""
    
    # Run the sequential tests script
    & ".\run_sequential_tests.ps1" -ContinueOnFailure
}

# Add a pause when running from a window so the user can see the results
if ($Host.Name -eq "ConsoleHost") {
    Write-Host "`nPress any key to continue..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
