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
#
# Works on both systemd machines and init-less containers: if systemd isn't
# running as PID 1, tailscaled is started directly in the background instead
# of via `systemctl`.

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

has_systemd() {
  [ -d /run/systemd/system ] && command -v systemctl >/dev/null 2>&1
}

start_tailscaled_standalone() {
  if pgrep -x tailscaled >/dev/null 2>&1; then
    echo "tailscaled is already running."
    return
  fi

  echo "No systemd detected; starting tailscaled directly..."
  $SUDO mkdir -p /var/lib/tailscale /var/run/tailscale
  $SUDO nohup tailscaled \
    --state=/var/lib/tailscale/tailscaled.state \
    --socket=/var/run/tailscale/tailscaled.sock \
    >/var/log/tailscaled.log 2>&1 &
  disown || true

  for _ in $(seq 1 20); do
    [ -S /var/run/tailscale/tailscaled.sock ] && return
    sleep 0.5
  done

  echo "tailscaled did not start; see /var/log/tailscaled.log" >&2
  exit 1
}

if has_systemd; then
  $SUDO systemctl enable --now tailscaled
else
  start_tailscaled_standalone
fi

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
