#!/usr/bin/env bash
#
# Installs Tailscale and enables Tailscale SSH on this machine.
#
# Usage:
#   ./install-tailscale-ssh.sh                  # installs Tailscale, then prompts you to log in
#   TS_AUTHKEY=tskey-... ./install-tailscale-ssh.sh   # installs and authenticates non-interactively
#
# Env vars:
#   TS_AUTHKEY     Tailscale auth key (https://login.tailscale.com/admin/settings/keys).
#                  If unset, `tailscale up` will print a login link to authenticate manually.
#   TS_HOSTNAME    Optional hostname to advertise to your tailnet.

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  SUDO="sudo"
else
  SUDO=""
fi

if ! command -v tailscale >/dev/null 2>&1; then
  echo "Installing Tailscale..."
  curl -fsSL https://tailscale.com/install.sh | $SUDO sh
else
  echo "Tailscale is already installed."
fi

$SUDO systemctl enable --now tailscaled

UP_ARGS=(--ssh)
if [ -n "${TS_AUTHKEY:-}" ]; then
  UP_ARGS+=(--authkey "${TS_AUTHKEY}")
fi
if [ -n "${TS_HOSTNAME:-}" ]; then
  UP_ARGS+=(--hostname "${TS_HOSTNAME}")
fi

echo "Enabling Tailscale SSH..."
$SUDO tailscale up "${UP_ARGS[@]}"

echo
echo "Done. Tailscale SSH is enabled on this machine."
echo "From another device on your tailnet, connect with:"
echo "  ssh <user>@$($SUDO tailscale status --self --json 2>/dev/null | grep -m1 '"DNSName"' | cut -d'"' -f4 | sed 's/\.$//' || echo '<this-machine>')"
