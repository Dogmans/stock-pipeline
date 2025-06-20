# Documentation Management

<#
.SYNOPSIS
Lists and manages documentation files in the project.

.DESCRIPTION
This script helps find and manage documentation across the project structure.

.PARAMETER SearchTerm
Optional. A search term to look for in documentation files.

.PARAMETER NewNote
Creates a new daily note for today.

.EXAMPLE
./manage_docs.ps1 -SearchTerm "provider"
Searches documentation files for the term "provider".

.EXAMPLE
./manage_docs.ps1 -NewNote
Creates a new daily note file with today's date.
#>

param(
    [string]$SearchTerm,
    [switch]$NewNote
)

# Function to create a new daily note
function New-DailyNote {
    $today = Get-Date -Format "yyyy-MM-dd"
    $filePath = "docs/daily_notes/$today.md"
    
    if (Test-Path $filePath) {
        Write-Host "Daily note for $today already exists at $filePath"
    }
    else {
        @"
# Development Notes - $today

## Summary

[Brief summary of today's work]

## Tasks Completed

- 

## Issues Encountered

-

## Next Steps

-

"@ | Out-File -FilePath $filePath -Encoding utf8
        Write-Host "Created new daily note at $filePath"
    }
    
    # Open the file in VS Code
    code $filePath
}

# Function to search documentation
function Search-Documentation {
    param([string]$Term)
    
    $files = Get-ChildItem -Path "docs", "scripts" -Recurse -Include "*.md", "*.ps1", "*.py"
    
    foreach ($file in $files) {
        $content = Get-Content $file.FullName -Raw
        if ($content -match $Term) {
            Write-Host "Found match in $($file.FullName):"
            $matchContext = (Get-Content $file.FullName | Select-String $Term -Context 2,2)
            $matchContext | ForEach-Object {
                Write-Host "  $_" -ForegroundColor Yellow
            }
            Write-Host ""
        }
    }
}

# Main script execution
if ($NewNote) {
    New-DailyNote
}
elseif ($SearchTerm) {
    Search-Documentation -Term $SearchTerm
}
else {
    Write-Host "Documentation Structure:"
    Write-Host "----------------------"
    Write-Host "/docs"
    Write-Host "  /daily_notes - Day-by-day development notes"
    Write-Host "  /guides - Detailed guides on specific topics"
    Write-Host "/scripts"
    Write-Host "  /powershell - PowerShell script examples"
    Write-Host "  /python - Python script examples"
    Write-Host ""
    Write-Host "Use -SearchTerm to search documentation or -NewNote to create a daily note."
}
