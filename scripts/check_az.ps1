Write-Host "===AZ_CHECK_START==="
if (Test-Path 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd') {
    Write-Host "STATUS: INSTALLED"
    & 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd' --version 2>&1 | Select-Object -First 3
} else {
    Write-Host "STATUS: NOT_INSTALLED"
    $msiPath = Join-Path $env:TEMP 'azure-cli.msi'
    if (Test-Path $msiPath) {
        $size = (Get-Item $msiPath).Length
        Write-Host "MSI exists at $msiPath, size: $size bytes"
        if ($size -gt 60000000) {
            Write-Host "MSI download complete. Installing..."
            Start-Process msiexec.exe -ArgumentList '/i', $msiPath, '/quiet', '/norestart' -Wait
            Write-Host "INSTALL_DONE"
        } else {
            Write-Host "MSI download incomplete ($size / ~64MB)"
        }
    } else {
        Write-Host "No MSI found. Need fresh download."
    }
}
Write-Host "===AZ_CHECK_END==="
