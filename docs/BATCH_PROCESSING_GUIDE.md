# Batch Processing Guide for Subtitle Translation

## Overview
This guide demonstrates how to process multiple subtitle files efficiently using the MarianMT backend for high-performance translation.

## Performance Expectations
- Small episodes (300-500 entries): ~30-60 seconds each
- Medium episodes (600-800 entries): ~1-2 minutes each
- Large episodes (900-1200 entries): ~2-4 minutes each

## Basic Batch Processing

### Single Directory Processing
```powershell
# Process all SRT files in a directory
Get-ChildItem ".\subtitles\season01\*.srt" | ForEach-Object {
    Write-Host "Processing: $($_.Name)"
    python main.py $_.FullName --backend marian --verbose
}
```

### Multiple Directory Processing
```powershell
# Process files from multiple seasons
$seasons = @("season01", "season02", "season03")
foreach ($season in $seasons) {
    Write-Host "Processing $season..." -ForegroundColor Yellow
    Get-ChildItem ".\subtitles\$season\*.srt" | ForEach-Object {
        Write-Host "Translating: $($_.Name)" -ForegroundColor Cyan
        python main.py $_.FullName --backend marian --verbose
    }
}
```

## Advanced Batch Processing Examples

### Sequential Episode Processing
```powershell
# Process episodes with sequential numbering
for ($i = 1; $i -le 22; $i++) {
    $episode = $i.ToString("00")
    $inputFile = ".\subtitles\series\episode_$episode.srt"
    if (Test-Path $inputFile) {
        Write-Host "Processing Episode $episode..."
        python main.py $inputFile --backend marian --verbose
    }
}
```

### Custom Output Directory
```powershell
# Process with custom output location
Get-ChildItem ".\input\*.srt" | ForEach-Object {
    $outputFile = ".\output\translated_$($_.BaseName).hu.srt"
    python main.py $_.FullName --backend marian --output $outputFile --verbose
}
```

### Filtered Processing
```powershell
# Process only files matching specific pattern
Get-ChildItem ".\subtitles\*.srt" | Where-Object { $_.Name -like "*sample*" } | ForEach-Object {
    python main.py $_.FullName --backend marian --verbose
}
```

## Error Handling and Resume

### Resume Interrupted Processing
```powershell
# Resume processing with error handling
Get-ChildItem ".\subtitles\*.srt" | ForEach-Object {
    $progressFile = "$($_.DirectoryName)\$($_.BaseName).hu.progress"
    if (Test-Path $progressFile) {
        Write-Host "Resuming: $($_.Name)" -ForegroundColor Green
        python main.py $_.FullName --backend marian --resume --verbose
    } else {
        Write-Host "Starting: $($_.Name)" -ForegroundColor Cyan
        python main.py $_.FullName --backend marian --verbose
    }
}
```

### Batch Processing with Error Logging
```powershell
# Process with comprehensive error logging
$logFile = "batch_translation_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
Get-ChildItem ".\subtitles\*.srt" | ForEach-Object {
    try {
        Write-Host "Processing: $($_.Name)" -ForegroundColor Cyan
        $result = python main.py $_.FullName --backend marian --verbose 2>&1
        "$($_.Name): SUCCESS" | Add-Content $logFile
        $result | Add-Content $logFile
    }
    catch {
        Write-Host "ERROR processing $($_.Name): $_" -ForegroundColor Red
        "$($_.Name): ERROR - $_" | Add-Content $logFile
    }
}
```

## Performance Optimization

### Parallel Processing (PowerShell 7+)
```powershell
# Process multiple files in parallel (use with caution on memory)
Get-ChildItem ".\subtitles\*.srt" | ForEach-Object -Parallel {
    python main.py $_.FullName --backend marian --verbose
} -ThrottleLimit 3
```

### Background Processing
```powershell
# Start background jobs for long-running batches
$jobs = @()
Get-ChildItem ".\subtitles\large_files\*.srt" | ForEach-Object {
    $job = Start-Job -ScriptBlock {
        param($filePath)
        python main.py $filePath --backend marian --verbose
    } -ArgumentList $_.FullName
    $jobs += $job
}

# Wait for all jobs to complete
$jobs | Wait-Job | Receive-Job
```

## Sample File Structure

### Recommended Directory Organization
```
project/
├── subtitles/
│   ├── series_a/
│   │   ├── episode_01.srt
│   │   ├── episode_02.srt
│   │   └── ...
│   ├── series_b/
│   │   ├── s01e01.srt
│   │   ├── s01e02.srt
│   │   └── ...
│   └── samples/
│       ├── test_sample.srt
│       └── demo_file.srt
└── output/
    ├── translated/
    └── logs/
```

### Processing by Directory Structure
```powershell
# Process organized directory structure
$seriesDirectories = Get-ChildItem ".\subtitles\" -Directory
foreach ($series in $seriesDirectories) {
    Write-Host "Processing series: $($series.Name)" -ForegroundColor Green
    Get-ChildItem "$($series.FullName)\*.srt" | ForEach-Object {
        $outputDir = ".\output\$($series.Name)"
        if (!(Test-Path $outputDir)) { New-Item -ItemType Directory -Path $outputDir }
        $outputFile = "$outputDir\$($_.BaseName).hu.srt"
        python main.py $_.FullName --backend marian --output $outputFile --verbose
    }
}
```

## Monitoring and Progress

### Progress Monitoring Script
```powershell
# Monitor batch processing progress
function Show-TranslationProgress {
    param($directory)
    
    $totalFiles = (Get-ChildItem "$directory\*.srt").Count
    $completedFiles = (Get-ChildItem "$directory\*.hu.srt").Count
    $progressFiles = (Get-ChildItem "$directory\*.progress").Count
    
    Write-Host "Total files: $totalFiles" -ForegroundColor White
    Write-Host "Completed: $completedFiles" -ForegroundColor Green
    Write-Host "In progress: $progressFiles" -ForegroundColor Yellow
    Write-Host "Remaining: $($totalFiles - $completedFiles - $progressFiles)" -ForegroundColor Red
}

# Usage
Show-TranslationProgress ".\subtitles\season01"
```

### Completion Notification
```powershell
# Complete batch with notification
Get-ChildItem ".\subtitles\*.srt" | ForEach-Object {
    python main.py $_.FullName --backend marian --verbose
}
Write-Host "🎉 Batch translation completed!" -ForegroundColor Green
# Optional: System notification
[System.Windows.Forms.MessageBox]::Show("Batch translation completed!", "Translation Status")
```

## Best Practices

1. **Test First**: Always test with a small sample before processing large batches
2. **Monitor Resources**: Watch CPU/GPU usage during batch processing
3. **Use Resume**: Enable resume functionality for long-running batches
4. **Organize Output**: Use consistent naming and directory structure
5. **Log Everything**: Keep detailed logs for troubleshooting
6. **Backup Progress**: Progress files enable safe interruption and resume

## Common Patterns

### Development/Testing Pattern
```powershell
# Process only test files during development
Get-ChildItem ".\subtitles\*test*.srt" | ForEach-Object {
    python main.py $_.FullName --backend marian --verbose
}
```

### Production Pattern
```powershell
# Production batch with full logging and error handling
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logDir = ".\logs\batch_$timestamp"
New-Item -ItemType Directory -Path $logDir -Force

Get-ChildItem ".\subtitles\production\*.srt" | ForEach-Object {
    $logFile = "$logDir\$($_.BaseName).log"
    try {
        python main.py $_.FullName --backend marian --verbose > $logFile 2>&1
        Write-Host "✅ $($_.Name)" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ $($_.Name): $_" -ForegroundColor Red
        "ERROR: $_" | Add-Content $logFile
    }
}
```

This guide provides comprehensive batch processing capabilities while maintaining neutrality and avoiding any copyrighted content.
