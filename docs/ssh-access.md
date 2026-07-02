# Making your PC accessible via SSH

This guide (and the scripts in `scripts/`) enables an SSH server on your PC so
you can connect to it remotely with `ssh <user>@<ip>`.

## Linux

```bash
sudo bash scripts/setup-ssh-linux.sh
```

The script installs `openssh-server` (apt/dnf/pacman), enables `sshd` at boot,
opens port 22 in ufw/firewalld if one is active, and applies basic hardening
(no root login, limited auth tries).

## Windows 10 / 11

Run from an **Administrator** PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup-ssh-windows.ps1
```

Installs the built-in OpenSSH Server feature, starts it, sets it to start at
boot, and opens the firewall port.

## macOS

No script needed — enable the built-in server:

```bash
sudo systemsetup -setremotelogin on
```

(or System Settings → General → Sharing → Remote Login).

## Connecting

From another machine on the same network:

```bash
ssh <your-username>@<pc-ip-address>
```

Find the PC's IP with `hostname -I` (Linux), `ipconfig` (Windows), or
`ipconfig getifaddr en0` (macOS).

## Recommended: key-based authentication

On the **client** machine:

```bash
ssh-keygen -t ed25519          # if you don't already have a key
ssh-copy-id <user>@<pc-ip>     # copies your public key to the PC
```

Then disable password logins on the PC (Linux):

```bash
echo 'PasswordAuthentication no' | sudo tee -a /etc/ssh/sshd_config.d/99-hardening.conf
sudo systemctl reload ssh || sudo systemctl reload sshd
```

## Access from outside your home network

Port-forwarding 22 on your router exposes the PC to the internet — only do it
with key-only auth enabled. A safer option is an overlay network such as
Tailscale or WireGuard, which gives you SSH access from anywhere without
opening any router ports.
