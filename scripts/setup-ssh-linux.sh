#!/usr/bin/env bash
# Enable SSH access on this machine (Debian/Ubuntu, Fedora/RHEL, or Arch).
# Run with: sudo bash scripts/setup-ssh-linux.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Please run as root: sudo bash $0" >&2
    exit 1
fi

echo "==> Installing OpenSSH server..."
if command -v apt-get >/dev/null; then
    apt-get update -qq && apt-get install -y openssh-server
elif command -v dnf >/dev/null; then
    dnf install -y openssh-server
elif command -v pacman >/dev/null; then
    pacman -S --noconfirm --needed openssh
else
    echo "Unsupported distro: install openssh-server manually." >&2
    exit 1
fi

echo "==> Enabling and starting sshd..."
systemctl enable --now ssh 2>/dev/null || systemctl enable --now sshd

echo "==> Opening firewall port 22 (if a firewall is active)..."
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
    ufw allow ssh
elif command -v firewall-cmd >/dev/null && firewall-cmd --state &>/dev/null; then
    firewall-cmd --permanent --add-service=ssh
    firewall-cmd --reload
fi

echo "==> Applying basic hardening (key auth preferred, no root login)..."
mkdir -p /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/99-hardening.conf <<'EOF'
PermitRootLogin no
MaxAuthTries 4
X11Forwarding no
EOF
systemctl reload ssh 2>/dev/null || systemctl reload sshd

IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo
echo "Done. SSH is running. Connect from another machine with:"
echo "    ssh $(logname 2>/dev/null || echo '<user>')@${IP:-<this-machine-ip>}"
echo
echo "Tip: set up key-based auth from your client, then disable passwords:"
echo "    ssh-copy-id <user>@${IP:-<ip>}"
echo "    echo 'PasswordAuthentication no' | sudo tee -a /etc/ssh/sshd_config.d/99-hardening.conf"
echo "    sudo systemctl reload ssh || sudo systemctl reload sshd"
