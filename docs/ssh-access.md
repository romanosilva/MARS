# SSH access to your Windows PC via Tailscale

This setup makes your Windows PC reachable over SSH from any of your devices,
anywhere, through [Tailscale](https://tailscale.com)'s encrypted overlay
network — with **no router port-forwarding and nothing exposed to the LAN or
internet**. The firewall only accepts SSH from your tailnet.

## Setup (on the PC)

Run from an **Administrator** PowerShell in the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup-ssh-windows.ps1
```

The script:

1. Installs Tailscale (via `winget`) and logs you in — a browser window opens
   to authenticate.
2. Installs and starts Windows' built-in **OpenSSH Server**, set to start at
   boot. (Tailscale's own SSH server isn't available on Windows, so the PC
   runs standard sshd, reached over the tailnet.)
3. Replaces the default open firewall rule with one that allows port 22
   **only from Tailscale addresses** (`100.64.0.0/10`).

## Connecting (from your other devices)

Install Tailscale on the client (laptop, phone, etc.) and log in with the
same account. Then:

```
ssh <windows-user>@<pc-name>
```

With MagicDNS (on by default) the PC's machine name works directly; otherwise
use its Tailscale IP, shown by `tailscale ip -4` on the PC or in the
[admin console](https://login.tailscale.com/admin/machines) machine list.

Log in with your Windows account password, or set up key auth
(`ssh-copy-id`-style: append your public key to
`C:\ProgramData\ssh\administrators_authorized_keys` for admin accounts, or
`C:\Users\<user>\.ssh\authorized_keys` for standard accounts).

## Managing access

Who may SSH to the PC is controlled by your Windows accounts plus your
[tailnet ACLs](https://login.tailscale.com/admin/acls) — remove a device from
the tailnet and it loses all access instantly.

## Troubleshooting

- `ssh` times out → check both devices show as connected in `tailscale status`.
- Connection refused → check the service: `Get-Service sshd` (should be
  `Running`).
- Wrong shell → OpenSSH defaults to `cmd.exe`; to get PowerShell:

  ```powershell
  New-ItemProperty -Path "HKLM:\SOFTWARE\OpenSSH" -Name DefaultShell `
    -Value "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -PropertyType String -Force
  ```
