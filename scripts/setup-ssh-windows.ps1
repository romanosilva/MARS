# Enable SSH access on this Windows PC (Windows 10 1809+ / Windows 11).
# Run from an elevated (Administrator) PowerShell:
#   powershell -ExecutionPolicy Bypass -File scripts\setup-ssh-windows.ps1

#Requires -RunAsAdministrator

Write-Host "==> Installing OpenSSH Server..."
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

Write-Host "==> Starting sshd and enabling it at boot..."
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic

Write-Host "==> Opening firewall port 22..."
if (-not (Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -DisplayName "OpenSSH Server (sshd)" `
        -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
}

$ip = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.InterfaceAlias -notmatch 'Loopback' } |
    Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "Done. SSH is running. Connect from another machine with:"
Write-Host "    ssh $env:USERNAME@$ip"
