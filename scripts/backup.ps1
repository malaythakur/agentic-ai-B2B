# PostgreSQL Backup Script for Windows
# Run this script to backup the database

param(
    [string]$BackupDir = ".\backups",
    [string]$DbName = "ai_saas",
    [int]$RetentionDays = 7
)

$ErrorActionPreference = "Stop"

# Create backup directory if it doesn't exist
if (!(Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
    Write-Host "Created backup directory: $BackupDir"
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupFile = Join-Path $BackupDir "backup_${DbName}_${Timestamp}.sql"

Write-Host "Starting backup of database: $DbName"
Write-Host "Backup file: $BackupFile"

try {
    # Perform backup
    if ($env:DATABASE_URL) {
        # Use DATABASE_URL if available
        $env:PGPASSWORD = ($env:DATABASE_URL -split ":")[2] -split "@" | Select-Object -First 1
        pg_dump $env:DATABASE_URL > $BackupFile
    } else {
        # Use local connection
        pg_dump -Fc $DbName > "${BackupFile}.dump"
    }
    
    # Compress backup
    Compress-Archive -Path $BackupFile -DestinationPath "${BackupFile}.zip" -Force
    Remove-Item $BackupFile
    
    Write-Host "Backup completed: ${BackupFile}.zip"
    
    # Cleanup old backups
    $CutoffDate = (Get-Date).AddDays(-$RetentionDays)
    Get-ChildItem -Path $BackupDir -Filter "backup_*.zip" | 
        Where-Object { $_.LastWriteTime -lt $CutoffDate } |
        Remove-Item -Force
    
    Write-Host "Cleaned up backups older than $RetentionDays days"
    
    # Optional: Upload to Azure Blob if configured
    if ($env:AZURE_STORAGE_CONNECTION_STRING) {
        Write-Host "Uploading to Azure Blob Storage..."
        $ContainerName = "backups"
        $BlobName = "backup_${DbName}_${Timestamp}.zip"
        az storage blob upload --file "${BackupFile}.zip" --name $BlobName --container-name $ContainerName
        Write-Host "Upload completed"
    }
    
    Write-Host "Backup process completed successfully"
    
} catch {
    Write-Error "Backup failed: $_"
    exit 1
}
