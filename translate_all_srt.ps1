#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Batch translate all SRT files in the subtitles folder using MarianMT backend.

.DESCRIPTION
    This script finds all .srt files in the subtitles folder (including subdirectories)
    and translates them using the MarianMT backend with smart multiline strategy and
    cross-entry detection. Output files are created with .hun.srt extension.

.PARAMETER SubtitlesPath
    Path to the subtitles folder. Defaults to "subtitles"

.PARAMETER OutputPath
    Path to the output folder. Defaults to "output"

.PARAMETER Verbose
    Enable verbose output for detailed translation progress

.PARAMETER DryRun
    Show what files would be processed without actually translating them

.EXAMPLE
    .\translate_all_srt.ps1
    Translates all SRT files in "subtitles" folder to "output" folder

.EXAMPLE
    .\translate_all_srt.ps1 -Verbose
    Translates with detailed progress output

.EXAMPLE
    .\translate_all_srt.ps1 -DryRun
    Shows what files would be processed without translating
#>

param(
    [string]$SubtitlesPath = "subtitles",
    [string]$OutputPath = "output", 
    [switch]$Verbose,
    [switch]$DryRun
)

# Colors for output
$Green = "`e[32m"
$Yellow = "`e[33m"
$Red = "`e[31m"
$Blue = "`e[34m"
$Reset = "`e[0m"

Write-Host "${Blue}🎬 Subtitle Assistant - Batch Translation Script${Reset}" -ForegroundColor Blue
Write-Host "===============================================" -ForegroundColor Blue
Write-Host ""

# Check if subtitles folder exists
if (-not (Test-Path $SubtitlesPath)) {
    Write-Host "${Red}❌ Error: Subtitles folder '$SubtitlesPath' not found!${Reset}" -ForegroundColor Red
    Write-Host "Please make sure the subtitles folder exists and contains .srt files." -ForegroundColor Red
    exit 1
}

# Create output directory if it doesn't exist
if (-not (Test-Path $OutputPath)) {
    Write-Host "${Yellow}📁 Creating output directory: $OutputPath${Reset}" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
}

# Find all SRT files
Write-Host "${Blue}🔍 Scanning for SRT files in: $SubtitlesPath${Reset}" -ForegroundColor Blue
$srtFiles = Get-ChildItem -Path $SubtitlesPath -Filter "*.srt" -Recurse | Where-Object { $_.Name -notlike "*.hun.srt" -and $_.Name -notlike "*.hu.srt" }

if ($srtFiles.Count -eq 0) {
    Write-Host "${Yellow}⚠️  No SRT files found in '$SubtitlesPath'${Reset}" -ForegroundColor Yellow
    Write-Host "Make sure you have .srt files in the subtitles folder." -ForegroundColor Yellow
    exit 0
}

Write-Host "${Green}✅ Found $($srtFiles.Count) SRT files to translate${Reset}" -ForegroundColor Green
Write-Host ""

# Show files that will be processed
Write-Host "${Blue}📋 Files to be processed:${Reset}" -ForegroundColor Blue
foreach ($file in $srtFiles) {
    $relativePath = $file.FullName.Replace((Get-Location).Path + "\", "")
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
    $outputFile = Join-Path $OutputPath "$baseName.hun.srt"
    
    Write-Host "  📄 Input:  $relativePath" -ForegroundColor Cyan
    Write-Host "  📤 Output: $outputFile" -ForegroundColor Green
    Write-Host ""
}

if ($DryRun) {
    Write-Host "${Yellow}🏃 Dry run completed. No files were translated.${Reset}" -ForegroundColor Yellow
    Write-Host "Remove -DryRun parameter to perform actual translation." -ForegroundColor Yellow
    exit 0
}

# Confirm before proceeding
Write-Host "${Yellow}❓ Do you want to proceed with translation? [Y/N]${Reset}" -ForegroundColor Yellow -NoNewline
$confirmation = Read-Host
if ($confirmation -notmatch '^[Yy]') {
    Write-Host "${Yellow}❌ Translation cancelled by user.${Reset}" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "${Green}🚀 Starting batch translation with MarianMT...${Reset}" -ForegroundColor Green
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  - Backend: MarianMT (Helsinki-NLP/opus-mt-en-hu)" -ForegroundColor Cyan
Write-Host "  - Strategy: Smart multiline with cross-entry detection" -ForegroundColor Cyan
Write-Host "  - Mode: Line-by-line (resumable)" -ForegroundColor Cyan
Write-Host ""

# Process each file
$successCount = 0
$errorCount = 0
$startTime = Get-Date

foreach ($file in $srtFiles) {
    $fileNumber = $srtFiles.IndexOf($file) + 1
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
    $outputFile = Join-Path $OutputPath "$baseName.hun.srt"
    
    Write-Host "${Blue}[$fileNumber/$($srtFiles.Count)] Processing: $($file.Name)${Reset}" -ForegroundColor Blue
    
    # Build the command arguments
    $arguments = @(
        "main.py",
        "`"$($file.FullName)`"",
        "--backend", "marian",
        "--output", "`"$outputFile`"",
        "--multiline-strategy", "smart",
        "--cross-entry-detection"
    )
    
    if ($Verbose) {
        $arguments += "--verbose"
    }
    
    # Execute translation
    try {
        $startFileTime = Get-Date
        
        if ($Verbose) {
            Write-Host "  Command: python $($arguments -join ' ')" -ForegroundColor DarkGray
        }
        
        $process = Start-Process -FilePath "python" -ArgumentList $arguments -Wait -PassThru -NoNewWindow
        
        $endFileTime = Get-Date
        $fileElapsed = ($endFileTime - $startFileTime).TotalSeconds
        
        if ($process.ExitCode -eq 0) {
            Write-Host "  ${Green}✅ Success${Reset} (${fileElapsed:F1}s)" -ForegroundColor Green
            $successCount++
        } else {
            Write-Host "  ${Red}❌ Failed${Reset} (Exit code: $($process.ExitCode))" -ForegroundColor Red
            $errorCount++
        }
    }
    catch {
        Write-Host "  ${Red}❌ Error: $($_.Exception.Message)${Reset}" -ForegroundColor Red
        $errorCount++
    }
    
    Write-Host ""
}

# Final summary
$endTime = Get-Date
$totalElapsed = ($endTime - $startTime).TotalMinutes

Write-Host "===============================================" -ForegroundColor Blue
Write-Host "${Blue}🏁 Batch Translation Complete!${Reset}" -ForegroundColor Blue
Write-Host ""
Write-Host "Results:" -ForegroundColor Cyan
Write-Host "  ✅ Successful: $successCount files" -ForegroundColor Green
Write-Host "  ❌ Failed: $errorCount files" -ForegroundColor Red
Write-Host "  ⏱️  Total time: ${totalElapsed:F1} minutes" -ForegroundColor Cyan
Write-Host ""

if ($successCount -gt 0) {
    Write-Host "${Green}🎉 Translated files are available in: $OutputPath${Reset}" -ForegroundColor Green
    Write-Host "File naming pattern: [original_name].hun.srt" -ForegroundColor Cyan
}

if ($errorCount -gt 0) {
    Write-Host "${Yellow}⚠️  Some files failed to translate. Check the output above for details.${Reset}" -ForegroundColor Yellow
    Write-Host "You can re-run the script to retry failed translations (existing files will be skipped)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "${Blue}🎬 Thank you for using Subtitle Assistant!${Reset}" -ForegroundColor Blue
