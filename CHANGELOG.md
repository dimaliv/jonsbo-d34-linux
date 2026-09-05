# Changelog

Notable changes are listed here. Version numbers follow Semantic Versioning;
hardware support is experimental during the 0.x series.

## 0.1.0 — 2026-09-05

### Added

- Jonsbo D34 numeric HID output using the Python standard library.
- Ryzen CPU and Radeon GPU sensors; largest-VRAM Radeon selection.
- Separate 200 ms USB updates and configurable CPU frequency sampling (default 1 s).
- Local clock/date, CPU/GPU temperatures and utilization, GPU power/clock and RAM usage.
- Descriptor validation, reconnection, single-instance locking and interruptible shutdown.
- User-service installer/uninstaller preserving configuration and independent of the checkout.
- English/Russian documentation, upstream protocol attribution and MIT licensing.
- Hardware-independent tests, formatting checks and package-build CI.
