import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jonsbo_d34.sensors import Sensors


class SensorTests(unittest.TestCase):
    def test_discrete_gpu_selected_and_optional_readings_default_to_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixtures = {
                "hwmon0/name": "k10temp",
                "hwmon0/temp1_label": "Tctl",
                "hwmon0/temp1_input": "48500",
                "hwmon1/name": "amdgpu",
                "hwmon1/device/mem_info_vram_total": str(2 * 1024**3),
                "hwmon1/temp1_label": "edge",
                "hwmon1/temp1_input": "42000",
                "hwmon9/name": "amdgpu",
                "hwmon9/device/mem_info_vram_total": str(16 * 1024**3),
                "hwmon9/temp1_label": "edge",
                "hwmon9/temp1_input": "32000",
            }
            for name, value in fixtures.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(value)
            with patch("jonsbo_d34.sensors.HWMON", root):
                sensors = Sensors()
            self.assertEqual(sensors.gpu, root / "hwmon9")
            proc = {
                "/proc/cpuinfo": "cpu MHz : 4000\ncpu MHz : 5000",
                "/proc/stat": "cpu 100 0 100 800 0 0 0 0 0 0",
                "/proc/meminfo": "MemTotal: 1000 kB\nMemAvailable: 750 kB",
            }

            def fixture_read(path):
                return proc[str(path)] if str(path) in proc else Path(path).read_text().strip()

            with patch("jonsbo_d34.sensors.read", side_effect=fixture_read):
                values = sensors.sample()
                self.assertEqual(values["cpu_temp"], 48.5)
                self.assertEqual(values["gpu_temp"], 32)
                self.assertEqual(values["cpu_mhz"], 4500)
                self.assertEqual(values["gpu_power"], 0)
                self.assertEqual(values["ram_usage"], 25)
                proc["/proc/stat"] = "cpu 120 0 110 870 0 0 0 0 0 0"
                self.assertAlmostEqual(sensors.sample()["cpu_usage"], 30)
                (root / "hwmon9/temp1_input").unlink()
                with self.assertRaises(FileNotFoundError):
                    sensors.sample()
