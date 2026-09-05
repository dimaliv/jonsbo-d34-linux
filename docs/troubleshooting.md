# Troubleshooting

Start with these commands from the source directory:

```sh
python3 src/panel.py --diagnose
systemctl --user status jonsbo-d34.service
journalctl --user -u jonsbo-d34.service -n 40 --no-pager
lsusb -d 5131:2007
```

## USB access

The service needs write permission to the panel's hidraw interface. On the tested
SteamOS installation, the active desktop user already had an ACL granting access.
The installer does not alter system USB permissions.

If the log says `Permission denied`, the optional rule in `src/packaging/70-jonsbo-d34.rules`
grants access through logind to the active local user, limited to this VID/PID.
Review and install it only if needed:

```sh
sudo install -m 644 src/packaging/70-jonsbo-d34.rules /etc/udev/rules.d/70-jonsbo-d34.rules
sudo udevadm control --reload-rules
```

Reconnect the panel's USB connection when practical, or reboot, then restart the
user service. This is a system change and requires administrator privileges.
The rule does not grant world-writable access. For a headless service without an
active local session, an explicit group/access policy would be needed instead.

## Panel blinks

Keep `UPDATE_INTERVAL=0.2`. Increase `CPU_FREQ_INTERVAL` to slow the changing
frequency digits instead of slowing USB writes. The exact firmware timeout is unknown.

## CPU frequency jumps

The display shows a sampled mean across logical processors, not the base clock,
peak clock or an average over the sampling interval. CPU power management naturally
changes this value. Set `CPU_FREQ_INTERVAL=2` or `3` for less frequent changes.

## Missing sensor or wrong GPU

This release implements `k10temp/Tctl` and `amdgpu/edge`, not Intel or NVIDIA backends.
It selects the AMD GPU with the most VRAM. If two discrete cards have equal memory,
selection is not user-configurable; please include your hwmon layout in an issue.
The GPU temperature is edge temperature, not hotspot or VRAM temperature.

## Another instance is already running

Stop the service before running `--once` or a foreground instance. A per-user
advisory lock prevents two copies of this project writing concurrently. Other
vendor tools or projects do not share that lock; stop them separately.

## Service starts but the screen is blank

Check the journal for descriptor mismatches or write errors. Successful writes
do not prove that another firmware revision understands the same numeric fields.
Report the USB descriptor and case model; do not bypass the descriptor check blindly.

## Autostart and source edits

Autostart is tied to the systemd user session, not guaranteed before login. Local
USB ACLs may only become available when a session is active. The service retries.
The installer copies the runtime files: changing source files alone does not update
the installed program. Rerun `python3 src/scripts/install.py install` after source edits.

## Reporting a problem

Include the case model, OS/kernel/Python versions, CPU/GPU models, service log and
`--diagnose` output. Remove any unrelated personal paths or device identifiers you
do not want to share. State what the physical panel displays as well as what the log says.
