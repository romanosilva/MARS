# Making your PC accessible via SSH (over Tailscale)

The recommended setup uses [Tailscale](https://tailscale.com): your PC becomes
reachable from any of your devices, anywhere, over an encrypted overlay
network — with **no router port-forwarding and nothing exposed to the
internet**. Install Tailscale on the PC and on each client device, logged in
to the same account.

## Linux PC (recommended: Tailscale SSH)

```bash
sudo bash scripts/setup-tailscale-linux.sh
```

This installs Tailscale and runs `tailscale up --ssh`, enabling Tailscale's
built-in SSH server. You don't need `openssh-server`, open ports, or key
management — authentication is your tailnet identity, and access is governed
by your [tailnet ACLs](https://login.tailscale.com/admin/acls).

Connect from any device on your tailnet:

```bash
ssh <user>@<machine-name>   # MagicDNS name, or the 100.x.y.z Tailscale IP
```

## Windows 10 / 11 PC

Tailscale on Windows doesn't provide the built-in SSH *server*, so run a
standard OpenSSH server and reach it over the tailnet:

1. Install Tailscale from https://tailscale.com/download and log in.
2. From an **Administrator** PowerShell:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\setup-ssh-windows.ps1
   ```

3. Connect via the machine's Tailscale name/IP: `ssh <user>@<machine-name>`.

## macOS PC

1. Install Tailscale from https://tailscale.com/download and log in.
2. Enable the built-in SSH server:

   ```bash
   sudo systemsetup -setremotelogin on
   ```

   (or System Settings → General → Sharing → Remote Login)

3. Connect via the machine's Tailscale name/IP.

## Finding the machine's Tailscale address

On the PC: `tailscale ip -4`, or check the machine list in the
[admin console](https://login.tailscale.com/admin/machines). With MagicDNS
enabled (default), the machine name alone works: `ssh user@my-pc`.

## LAN-only alternative (no Tailscale)

If you only need access from the same local network, skip Tailscale and just
run the OpenSSH setup:

- Linux: `sudo bash scripts/setup-ssh-linux.sh`
- Windows: `scripts\setup-ssh-windows.ps1` (Administrator PowerShell)
- macOS: `sudo systemsetup -setremotelogin on`

Then connect with `ssh <user>@<lan-ip>`. If you go this route, prefer
key-based auth (`ssh-copy-id <user>@<ip>`, then set
`PasswordAuthentication no` in the sshd config) — and avoid forwarding
port 22 on your router; that's what Tailscale is for.
