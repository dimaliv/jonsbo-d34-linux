"""Read Linux hwmon and procfs sensors; cache CPU frequency separately."""

import logging
import time
from pathlib import Path

HWMON = Path("/sys/class/hwmon")


def read(path: str | Path) -> str:
    return Path(path).read_text().strip()


def optional_number(path: str | Path, default: int = 0) -> int:
    try:
        return int(read(path))
    except (OSError, ValueError):
        return default


def sensor(name: str, label: str) -> Path:
    for h in sorted(HWMON.glob("hwmon*")):
        if read(h / "name") == name:
            for p in h.glob("temp*_label"):
                if read(p) == label:
                    return p.with_name(p.name.replace("_label", "_input"))
    raise RuntimeError(f"Sensor missing: {name}/{label}")


class Sensors:
    """Discover Ryzen/Radeon sensors and retain CPU counters between samples."""

    def __init__(self, cpu_freq_interval=1.0):
        self.cpu_freq_interval = cpu_freq_interval
        self.cached_cpu_mhz = None
        self.next_cpu_freq_read = 0.0
        self.cpu = sensor("k10temp", "Tctl")
        gpus = [h for h in HWMON.glob("hwmon*") if read(h / "name") == "amdgpu"]
        if not gpus:
            raise RuntimeError("No AMD GPU sensors found")
        # Prefer discrete graphics when an integrated Radeon is also present.
        self.gpu = max(gpus, key=lambda h: optional_number(h / "device/mem_info_vram_total"))
        self.gpu_temp = next(
            (
                p.with_name(p.name.replace("_label", "_input"))
                for p in self.gpu.glob("temp*_label")
                if read(p) == "edge"
            ),
            self.gpu / "temp1_input",
        )
        self.previous_cpu = None
        logging.info("CPU: %s; GPU: %s", self.cpu, (self.gpu / "device").resolve())

    def cpu_frequency(self) -> float:
        """Return mean current MHz, reusing it until the monotonic deadline."""
        now = time.monotonic()
        if self.cached_cpu_mhz is None or now >= self.next_cpu_freq_read:
            freqs = [
                float(line.split(":")[1])
                for line in read("/proc/cpuinfo").splitlines()
                if line.startswith("cpu MHz")
            ]
            if not freqs:
                raise RuntimeError("CPU frequency unavailable")
            self.cached_cpu_mhz = sum(freqs) / len(freqs)
            self.next_cpu_freq_read = now + self.cpu_freq_interval
        return self.cached_cpu_mhz

    def sample(self) -> dict[str, float]:
        cpu_mhz = self.cpu_frequency()
        counts = list(map(int, read("/proc/stat").splitlines()[0].split()[1:9]))
        current = (sum(counts), counts[3] + counts[4])
        usage = 0
        if self.previous_cpu:
            total = current[0] - self.previous_cpu[0]
            if total > 0:
                usage = 100 * (1 - (current[1] - self.previous_cpu[1]) / total)
        self.previous_cpu = current
        memory = {
            line.split(":")[0]: int(line.split()[1]) for line in read("/proc/meminfo").splitlines()
        }
        return dict(
            cpu_temp=int(read(self.cpu)) / 1000,
            gpu_temp=int(read(self.gpu_temp)) / 1000,
            cpu_mhz=cpu_mhz,
            cpu_usage=usage,
            gpu_usage=optional_number(self.gpu / "device/gpu_busy_percent"),
            gpu_power=optional_number(self.gpu / "power1_average") / 1e6,
            gpu_mhz=optional_number(self.gpu / "freq1_input") / 1e6,
            ram_usage=100 * (1 - memory["MemAvailable"] / memory["MemTotal"]),
        )
