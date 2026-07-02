#!/usr/bin/env bash
# Make this machine reachable over SSH from anywhere via Tailscale.
# Uses Tailscale's built-in SSH server: no open ports, no sshd config,
# auth is handled by your tailnet identity.
# Run with: sudo bash scripts/setup-tailscale-linux.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Please run as root: sudo bash $0" >&2
    exit 1
fi

if ! command -v tailscale >/dev/null; then
    echo "==> Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
fi

echo "==> Bringing Tailscale up with SSH enabled..."
echo "    (a browser link will be printed - open it to authenticate)"
tailscale up --ssh

IP=$(tailscale ip -4 2>/dev/null | head -n1)
NAME=$(tailscale status --json 2>/dev/null | grep -o '"DNSName": *"[^"]*"' | head -n1 | cut -d'"' -f4 | sed 's/\.$//')

echo
echo "Done. This machine is now reachable from any device on your tailnet:"
echo "    ssh $(logname 2>/dev/null || echo '<user>')@${NAME:-$IP}"
echo
echo "Notes:"
echo "  - Install Tailscale on your client devices and log in with the same account."
echo "  - No router ports were opened; traffic goes over the encrypted tailnet."
echo "  - Manage who can SSH in via the ACLs at https://login.tailscale.com/admin/acls"
