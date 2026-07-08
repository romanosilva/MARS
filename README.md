# MARS

## Remote access via Tailscale SSH

`scripts/install-tailscale-ssh.sh` installs [Tailscale](https://tailscale.com/) on a machine
and enables [Tailscale SSH](https://tailscale.com/kb/1193/tailscale-ssh), so the machine can be
reached over `ssh` from any other device on the same tailnet without managing SSH keys or open
ports.

### Usage

```bash
./scripts/install-tailscale-ssh.sh
```

This installs the `tailscale` package, starts `tailscaled`, and runs `tailscale up --ssh`.
If no auth key is provided, `tailscale up` prints a login link to authenticate the machine
interactively.

On machines with systemd, `tailscaled` is started via `systemctl`. On init-less containers
(no `systemd` as PID 1), the script starts `tailscaled` directly in the background instead,
logging to `/var/log/tailscaled.log`.

This script needs outbound network access to `tailscale.com` (and the tailnet coordination
servers `*.tailscale.com`) to download and authenticate — it won't work in sandboxes whose
network policy blocks that host.

### Non-interactive setup

Generate an auth key from the [Tailscale admin console](https://login.tailscale.com/admin/settings/keys)
and pass it via environment variable to authenticate without a browser:

```bash
TS_AUTHKEY=tskey-... ./scripts/install-tailscale-ssh.sh
```

Optionally set `TS_HOSTNAME` to control the name the machine advertises on the tailnet:

```bash
TS_AUTHKEY=tskey-... TS_HOSTNAME=mars-rover-1 ./scripts/install-tailscale-ssh.sh
```

### Connecting

From another device on the same tailnet:

```bash
ssh <user>@<machine-name>
```

Use `tailscale status` to list machines and their tailnet names.
