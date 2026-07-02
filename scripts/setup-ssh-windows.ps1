# Make this Windows PC accessible via SSH over Tailscale.
# Installs Tailscale + the built-in OpenSSH Server, and allows SSH
# only from your tailnet (no ports exposed to the LAN or internet).
#
# Run from an elevated (Administrator) PowerShell:
#   powershell -ExecutionPolicy Bypass -File scripts\setup-ssh-windows.ps1

#Requires -RunAsAdministrator

$ErrorActionPreference = 'Stop'
$tailscaleExe = "$env:ProgramFiles\Tailscale\tailscale.exe"

Write-Host "==> Installing Tailscale..."
if (-not (Test-Path $tailscaleExe)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id Tailscale.Tailscale --accept-source-agreements --accept-package-agreements
    } else {
        Write-Error "winget not found. Install Tailscale manually from https://tailscale.com/download/windows and re-run this script."
    }
} else {
    Write-Host "    Tailscale already installed."
}

Write-Host "==> Logging in to Tailscale (a browser window/link will open)..."
& $tailscaleExe up

Write-Host "==> Installing OpenSSH Server..."
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

Write-Host "==> Starting sshd and enabling it at boot..."
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic

Write-Host "==> Allowing SSH only from the tailnet (100.64.0.0/10)..."
# Remove the wide-open rule the OpenSSH capability may have created.
Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -Name "OpenSSH-Tailscale-In-TCP" -DisplayName "OpenSSH Server (Tailscale only)" `
    -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 `
    -RemoteAddress 100.64.0.0/10

$tsIp = (& $tailscaleExe ip -4) | Select-Object -First 1

Write-Host ""
Write-Host "Done. From any device on your tailnet (with Tailscale installed and"
Write-Host "logged in to the same account), connect with:"
Write-Host "    ssh $env:USERNAME@$tsIp"
Write-Host ""
Write-Host "With MagicDNS (on by default) the machine name also works:"
Write-Host "    ssh $env:USERNAME@$env:COMPUTERNAME"
