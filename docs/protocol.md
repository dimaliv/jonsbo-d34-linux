# USB protocol notes

## Provenance

The report layout below follows
[coldwelderx/cooler-lcd-linux, PROTOCOL.md](https://github.com/coldwelderx/cooler-lcd-linux/blob/bb2ef86f71da423c0b160fdcb941f3a563b907fe/PROTOCOL.md).
The upstream author documents reverse engineering of **PC Monitor All**. This
project uses that description; it does not claim an independent protocol discovery.
See [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) for the upstream MIT notice.

## Transport verified on the tested D34

- USB vendor/product: `5131:2007`. USB name databases may call it an MSR card reader.
- Linux interface: `/dev/hidraw*`, found through `/sys/class/hidraw` on each reconnect.
- HID descriptor: one 64-byte input report and one 64-byte output report; no report IDs.
- Linux `write()` buffer: **65 bytes**, including the leading zero required by hidraw
  for an unnumbered report. The leading zero is API framing, not an additional payload byte.
- Packet cadence: 200 ms. A 1-second interval visibly blinked on the tested panel;
  the exact firmware timeout has not been measured.

Expected HID descriptor:

```text
06 00 ff 09 01 a1 01 09 02 15 00 26 00 ff 75 08
95 40 81 06 09 02 15 00 26 00 ff 75 08 95 40 91
06 c0
```

A descriptor mismatch is rejected, even when the VID/PID matches. A matching
descriptor alone does not prove protocol compatibility with a different product.

## Host write buffer

| Offset | Length | Meaning |
| --- | --- | --- |
| 0 | 1 | `00`: unnumbered report prefix for Linux hidraw |
| 1–3 | 3 | `00 01 02`: refresh header |
| 4–36 | 33 | Numeric values, indexed below |
| 37–64 | 28 | Zero padding |

## Values emitted by this implementation

| Value index | Meaning | Encoding / source |
| --- | --- | --- |
| 0–2 | CPU temperature / unit | Integer, hundredths, `0` for °C; `k10temp/Tctl` |
| 3 | CPU utilization | Percent, delta of `/proc/stat`; first sample is zero |
| 4–5, 31 | CPU power | Zero: no implemented source |
| 6–7 | CPU frequency | `high × 100 + low` MHz; mean of `/proc/cpuinfo` readings |
| 8–9 | CPU voltage | Zero: no implemented source |
| 10–12 | GPU temperature / unit | Integer, hundredths, `0` for °C; Radeon `edge` |
| 13 | GPU utilization | `gpu_busy_percent` |
| 14–15, 32 | GPU power | `v[32] × 100 + v[14] + v[15] / 100` W |
| 16–17 | GPU frequency | `high × 100 + low` MHz |
| 18–21 | Fan / pump speed | Zero: no implemented source |
| 22–23 | Year | Century, year within century |
| 24–28 | Date / time | Month, day, hour, minute, second; local system time |
| 29 | Weekday | Sunday = 0 |
| 30 | RAM utilization | `100 × (1 − MemAvailable / MemTotal)` |

Temperature/frequency/power values are truncated and clamped to their encodable
nonnegative ranges; percentages are clamped to 0–100. CPU frequency is sampled
independently of USB writes and held between readings. Clock fields are freshly
encoded for every packet. Displayed field selection is controlled by firmware.

## Failure behavior

Missing optional GPU readings produce zero. Failure of a required reading prevents
the next write, closes the HID handle and retries discovery after three seconds.
The display may retain old values or time out during that period. There is no
device-level acknowledgement of correct visual rendering: a successful `write()`
only confirms the host-side transfer. No shutdown/blanking command is sent.
